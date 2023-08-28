from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

SHEET_MEMBER_TRACKING = config.SHEET_MEMBER_TRACKING  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:E'
RANGE_LEADERBOARD = 'Weekly Participation!A2:F'
RANGE_WEEK_HEADER = 'Weekly Participation!N1'


def get_sheet():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        return sheet
    except HttpError as err:
        print(err)
        return None


def is_valid(week, datestr):
    sheet = get_sheet()
    result = sheet.values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                range=RANGE_WEEK_HEADER).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    header = values[0][0]
    return f'Week {week}' in header and datestr in header


def get_new_members():
    sheet = get_sheet()
    result = sheet.values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                range=RANGE_MEMBERS).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return []

    new_members = list(filter(lambda l: len(l) == 1, values))
    return [item for sublist in new_members for item in sublist]  # flatten


def get_leaderboard():
    sheet = get_sheet()
    result = sheet.values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                range=RANGE_LEADERBOARD).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    filtered = list(filter(lambda l: len(l) == 6 and int(l[4]) > 0, values))
    ordered_list = sorted(filtered, key=lambda l: float(l[0]))
    sorted_list = sorted(ordered_list, key=lambda l: float(l[4]), reverse=True)

    output = []
    current_score = None
    line = ''
    for member in sorted_list:
        index = member[0]
        score = member[4]
        discord_id = member[5]
        # print(f'{index}, {score}, {discord_id}')

        if score != current_score:
            if current_score is not None:
                output.append(line)
            line = f'{score} '
        line += f'{discord_id} '
        current_score = score

    if current_score is not None:
        output.append(line)

    # print(output)
    return output
