import itertools
from enum import Enum

import config
import sheets

SPREADSHEET_BOSS_PARTIES = config.SPREADSHEET_BOSS_PARTIES  # The ID of the boss parties spreadsheet
SHEET_BOSS_PARTIES_MEMBERS = config.SHEET_BOSS_PARTIES_MEMBERS  # The ID of the Members sheet
RANGE_BOSSES = 'Bosses!A2:B'
RANGE_PARTIES = 'Parties!A2:H'
RANGE_MEMBERS = 'Members!A2:C'

service = sheets.get_service()


class PartyStatus(Enum):
    open = 1
    full = 2
    exclusive = 3
    fill = 4
    retired = 5


SHEET_BOSSES_NAME = 0
SHEET_BOSSES_ROLE_COLOR = 1

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

    bosses = __get_bosses()

    # get all boss party roles by matching their names to the bosses
    parties = []
    for role in ctx.guild.roles:
        if role.name.find(' ') == -1 or role.name.find('Practice') != -1:
            continue

        if role.name[0:role.name.find(' ')] in bosses.keys():
            parties.append(role)

    parties.reverse()  # Roles are ordered bottom up for some reason
    print(parties)

    # get list of parties from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    print(f'Before:\n{parties_values}')
    parties_values_index = 0
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

        if parties_values_index == len(parties_values):  # More party roles than in data
            parties_values.insert(parties_values_index, [role_id, boss_name, party_number, status, member_count])
        elif parties_values[parties_values_index][SHEET_PARTIES_ROLE_ID] != role_id:  # Party role doesn't match data
            parties_values.insert(parties_values_index, [role_id, boss_name, party_number, status, member_count])
        else:  # Party role data already exists
            pass

        parties_values_index += 1

    print(f'After:\n{parties_values}')

    body = {
        'values': parties_values
    }

    # Update parties

    result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                                    valueInputOption="RAW", body=body).execute()

    # Get list of members from sheet

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_MEMBERS).execute()
    members_values = result.get('values', [])
    new_members_values = []
    print(f'Before:\n{members_values}')
    for party in parties:
        party_role_id = str(party.id)
        for member in party.members:
            member_user_id = str(member.id)
            try:
                next(members_value for members_value in members_values if
                     members_value[SHEET_MEMBERS_USER_ID] == member_user_id and members_value[
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

    # get list of bosses from sheet
    bosses = __get_bosses()

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses.keys():
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
    __update_party(party)

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
    members_values = result.get('values', [])

    delete_index = -1
    for members_value in members_values:
        if members_value[SHEET_MEMBERS_USER_ID] == str(member.id) and members_value[SHEET_MEMBERS_PARTY_ROLE_ID] == str(
                party.id):
            # Found the entry, remove it
            delete_index = members_values.index(members_value) + 1
            break

    if delete_index != -1:
        delete_body = {
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
        print(delete_body)
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_BOSS_PARTIES, body=delete_body).execute()

    # Remove role from user
    await member.remove_roles(party)

    # Update party data
    __update_party(party)

    # Success
    await ctx.send(f'Successfully removed {member.mention} from {party.mention}.')


async def create(ctx, boss_name):
    await ctx.defer()

    # get list of bosses from sheet
    bosses = __get_bosses()


def retire():
    pass


def __get_bosses():
    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    bosses_values = result.get('values', [])
    bosses = {}
    for bosses_value in bosses_values:
        bosses[bosses_value[0]] = bosses_value[1]
    print(bosses)
    return bosses


def __update_party(party):
    # Update party in parties sheet if party will be full
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    for parties_value in parties_values:
        if parties_value[SHEET_PARTIES_ROLE_ID] == str(party.id):  # The relevant party data
            parties_value[SHEET_PARTIES_MEMBER_COUNT] = str(len(party.members))
            if parties_value[SHEET_PARTIES_STATUS] == PartyStatus.open.name and len(party.members) == 6:
                # Update to full if it is open. Exclusive status remains
                parties_value[SHEET_PARTIES_STATUS] = PartyStatus.full.name
            elif parties_value[SHEET_PARTIES_STATUS] == PartyStatus.full.name and len(party.members) < 6:
                # Update to open if it is full. Exclusive status remains
                parties_value[SHEET_PARTIES_STATUS] = PartyStatus.open.name
            break
    body = {
        'values': parties_values
    }
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                           valueInputOption="RAW", body=body).execute()
