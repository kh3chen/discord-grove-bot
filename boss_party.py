import itertools
from googleapiclient.errors import HttpError

import config
import sheets

SHEET_BOSS_PARTIES = config.SHEET_BOSS_PARTIES  # The ID of the boss parties sheet
RANGE_BOSSES = 'Bosses!A:A'
RANGE_PARTIES = 'Parties!A2:D'
RANGE_MEMBERS = 'Members!A2:C'


def add(member, role, job):
    service = sheets.get_service()

    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    values = result.get('values', [])
    bosses = list(itertools.chain(*values))  # flatten
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
