import itertools
from googleapiclient.errors import HttpError
from enum import Enum

import config
import sheets

SPREADSHEET_BOSS_PARTIES = config.SPREADSHEET_BOSS_PARTIES  # The ID of the boss parties spreadsheet
SHEET_BOSS_PARTIES_MEMBERS = config.SHEET_BOSS_PARTIES_MEMBERS  # The ID of the Members sheet
RANGE_BOSSES = 'Bosses!A:A'
RANGE_PARTIES = 'Parties!A2:H'
RANGE_MEMBERS = 'Members!A2:C'


class PartyStatus(Enum):
    open = 1
    full = 2
    exclusive = 3
    fill = 4
    retired = 5


SHEET_PARTIES_ROLE_ID = 0
SHEET_PARTIES_BOSS_NAME = 1
SHEET_PARTIES_PARTY_NUMBER = 2
SHEET_PARTIES_STATUS = 3
SHEET_PARTIES_MEMBER_COUNT = 4
SHEET_PARTIES_WEEKDAY = 5
SHEET_PARTIES_TIME_OF_DAY = 6
SHEET_PARTIES_BOSS_LIST_MESSAGE_ID = 7

SHEET_MEMBERS_USER_ID = 0
SHEET_MEMBERS_PARTY_ROLE_ID = 1
SHEET_MEMBERS_JOB = 2


async def sync(ctx):
    await ctx.defer()

    service = sheets.get_service()

    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    values = result.get('values', [])
    bosses = set(list(itertools.chain(*values)))  # flatten and make set
    print(bosses)

    # get all boss party roles by matching their names to the bosses
    parties = []
    for role in ctx.guild.roles:
        if role.name.find(' ') == -1 or role.name.find('Practice') != -1:
            continue

        if role.name[0:role.name.find(' ')] in bosses:
            parties.append(role)

    parties.reverse()  # Roles are ordered bottom up for some reason
    print(parties)

    # get list of parties from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_data = result.get('values', [])
    print(f'Before:\n{parties_data}')
    parties_data_index = 0
    for party in parties:
        role_id = str(party.id)
        boss_name_first_space = party.name.find(' ')
        boss_name = party.name[0:boss_name_first_space]
        party_number = str(
            party.name[boss_name_first_space + 1 + party.name[boss_name_first_space + 1:].find(' ') + 1:])
        member_count = str(len(party.members))
        if party.name.find('Retired') != -1:
            status = PartyStatus.retired.name
        elif party.name.find('Fill') != -1:
            status = PartyStatus.fill.name
        elif len(party.members) == 6:
            status = PartyStatus.full.name
        else:
            status = PartyStatus.open.name

        if parties_data_index == len(parties_data):  # More party roles than in data
            parties_data.insert(parties_data_index, [role_id, boss_name, party_number, status, member_count])
        elif parties_data[parties_data_index][SHEET_PARTIES_ROLE_ID] != role_id:  # Party role doesn't match data
            parties_data.insert(parties_data_index, [role_id, boss_name, party_number, status, member_count])
        else:  # Party role data already exists
            pass

        parties_data_index += 1

    print(f'After:\n{parties_data}')

    body = {
        'values': parties_data
    }

    # Update parties

    result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                                    valueInputOption="RAW", body=body).execute()

    # Get list of members from sheet

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_MEMBERS).execute()
    members_data = result.get('values', [])
    new_members_values = []
    print(f'Before:\n{members_data}')
    for party in parties:
        party_role_id = str(party.id)
        for member in party.members:
            member_user_id = str(member.id)
            try:
                next(member_data for member_data in members_data if
                     member_data[SHEET_MEMBERS_USER_ID] == member_user_id and member_data[
                         SHEET_MEMBERS_PARTY_ROLE_ID] == party_role_id)
            except StopIteration:  # Could not find
                new_members_values.append([member_user_id, party_role_id])
                continue

    print(f'New members:\n{new_members_values}')

    body = {
        'values': new_members_values
    }
    result = service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
                                                    valueInputOption="RAW", body=body).execute()
    await ctx.send('Sync complete.')


async def add(ctx, member, party, job):
    await ctx.defer()

    service = sheets.get_service()

    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    values = result.get('values', [])
    bosses = set(list(itertools.chain(*values)))  # flatten and make set
    print(bosses)

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses:
        await ctx.send('Error - Invalid role, role must be a boss party.')
        return

    # Check if the user is already in the party
    if member in party.members:
        await ctx.send('Error - Member is already in the boss party.')
        return

    # Check if the party is already full
    if len(party.members) == 6:
        await ctx.send('Error - Boss party is already full.')
        return

    # Add member to member sheet
    body = {
        'values': [[str(member.id), str(party.id), job]]
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
        valueInputOption="RAW", body=body).execute()
    print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
    print(body)

    # Add role to user
    await member.add_roles(party)

    # Update party data
    update_party(party)

    # Success
    await ctx.send(f'Successfully added {member.mention} {job} to {party.mention}.')


async def remove(ctx, member, party):
    await ctx.defer()

    service = sheets.get_service()

    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    values = result.get('values', [])
    bosses = set(list(itertools.chain(*values)))  # flatten and make set
    print(bosses)

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses:
        await ctx.send('Error - Invalid role, role must be a boss party.')
        return

    # Check if the user is not in the party
    # Check if user has the role
    if member not in party.members:
        await ctx.send('Error - Member not in boss party.')
        return

    # Remove member from member sheet
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS).execute()
    members_data = result.get('values', [])

    delete_index = -1
    for member_data in members_data:
        if member_data[SHEET_MEMBERS_USER_ID] == str(member.id) and member_data[SHEET_MEMBERS_PARTY_ROLE_ID] == str(
                party.id):
            # Found the entry, remove it
            delete_index = members_data.index(member_data) + 1
            break

    if delete_index != -1:
        update_spreadsheet_data = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": SHEET_BOSS_PARTIES_MEMBERS,
                            "dimension": "ROWS",
                            "startIndex": delete_index,
                            "endIndex": delete_index + 1
                        }
                    }
                }
            ]
        }
        print(update_spreadsheet_data)
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_BOSS_PARTIES, body=update_spreadsheet_data).execute()

    # Remove role from user
    await member.remove_roles(party)

    # Update party data
    update_party(party)

    # Success
    await ctx.send(f'Successfully removed {member.mention} from {party.mention}.')


def update_party(party):
    service = sheets.get_service()
    # Update party in parties sheet if party will be full
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_data = result.get('values', [])
    for party_data in parties_data:
        if party_data[SHEET_PARTIES_ROLE_ID] == str(party.id):  # The relevant party data
            party_data[SHEET_PARTIES_MEMBER_COUNT] = str(len(party.members))
            if party_data[SHEET_PARTIES_STATUS] == PartyStatus.open.name and len(party.members) == 6:
                # Update to full if it is open. Exclusive status remains
                party_data[SHEET_PARTIES_STATUS] = PartyStatus.full.name
            elif party_data[SHEET_PARTIES_STATUS] == PartyStatus.full.name and len(party.members) < 6:
                # Update to open if it is full. Exclusive status remains
                party_data[SHEET_PARTIES_STATUS] = PartyStatus.open.name
            break
    body = {
        'values': parties_data
    }
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                           valueInputOption="RAW", body=body).execute()


def create_party():
    pass


def retire_party():
    pass
