import itertools
from googleapiclient.errors import HttpError
from enum import Enum

import config
import sheets

SHEET_BOSS_PARTIES = config.SHEET_BOSS_PARTIES  # The ID of the boss parties sheet
RANGE_BOSSES = 'Bosses!A:A'
RANGE_PARTIES = 'Parties!A2:E'
RANGE_MEMBERS = 'Members!A2:C'


class PartyStatus(Enum):
    open = 1
    full = 2
    exclusive = 3
    fill = 4
    retired = 5


def sync(ctx):
    service = sheets.get_service()

    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_BOSS_PARTIES,
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
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_BOSS_PARTIES,
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
        status = ''
        if party.name.find('Retired') != -1:
            status = PartyStatus.retired.name
        elif party.name.find('Fill') != -1:
            status = PartyStatus.fill.name
        elif len(party.members) == 6:
            status = PartyStatus.full.name
        else:
            status = PartyStatus.open.name

        if parties_data_index == len(parties_data):  # More party roles than in data
            parties_data.insert(parties_data_index, [role_id, boss_name, party_number, status])
        elif parties_data[parties_data_index][0] != role_id:  # Party role doesn't match data
            parties_data.insert(parties_data_index, [role_id, boss_name, party_number, status])

        parties_data_index += 1

    print(f'After:\n{parties_data}')

    body = {
        'values': parties_data
    }

    # update parties

    result = service.spreadsheets().values().update(spreadsheetId=SHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                                    valueInputOption="RAW", body=body).execute()

    # get list of members from sheet

    result = service.spreadsheets().values().get(spreadsheetId=SHEET_BOSS_PARTIES,
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
                     member_data[0] == member_user_id and member_data[1] == party_role_id)
            except StopIteration:  # Could not find
                new_members_values.append([member_user_id, party_role_id])
                continue

    print(f'New members:\n{new_members_values}')

    body = {
        'values': new_members_values
    }
    result = service.spreadsheets().values().append(spreadsheetId=SHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
                                                    valueInputOption="RAW", body=body).execute()
    pass


def add(member, role, job):
    service = sheets.get_service()

    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    values = result.get('values', [])
    bosses = set(list(itertools.chain(*values)))  # flatten and make set
    print(bosses)

    # Validate that this is a boss party role
    if role.name.find(' ') != -1 and role.name[0:role.name.find(' ')] not in bosses:
        return False

    # Check if the user already has the role, or the party is full
    if member in role.members or len(role.members) == 6:
        return False

    # Add to sheet
    body = {
        'values': [[str(member.id), str(role.id), job]]
    }
    try:
        service = sheets.get_service()
        result = service.spreadsheets().values().append(
            spreadsheetId=SHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
            valueInputOption="RAW", body=body).execute()
        print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
        print(body)
        return result
    except HttpError as error:
        print(f'An error occurred: {error}')

    return True  # On success


def remove(ctx, user, role):
    if user not in role.members:
        return

    # remove role from user
    # remove member from sheet


def create_party():
    pass


def retire_party():
    pass
