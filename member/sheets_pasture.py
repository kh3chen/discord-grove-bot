from googleapiclient.errors import HttpError

import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_PASTURE_PARTICIPATION = 'Pasture Participation!A3:ZZZ'
RANGE_WEEK_HEADER = 'Pasture Participation!J1'
RANGE_WEEK_SUBHEADER = 'Pasture Participation!J2:L2'
RANGE_WEEK = 'Pasture Participation!J3:L'


def is_valid(week, datestr):
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_WEEK_HEADER).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    header = values[0][0]
    return f'Week {week}' in header and datestr in header


class PastureParticipation:
    LENGTH = 5

    INDEX_INDEX = 0
    INDEX_GROVE_IGNS = 1
    INDEX_MULE_IGNS = 2
    INDEX_NAME = 3
    INDEX_DISCORD_MENTION = 4

    def __init__(self, index, grove_igns, mule_igns, name, discord_mention):
        try:
            self.index = int(index)
        except ValueError:
            self.index = -1
        self.grove_igns = str(grove_igns)
        self.mule_igns = str(mule_igns)
        self.name = str(name)
        self.discord_mention = str(discord_mention)

    @property
    def discord_id(self):
        return int(self.discord_mention.strip('<@>'))

    @staticmethod
    def from_sheets_value(mp_value: list[str]):
        mp_value = mp_value[:PastureParticipation.LENGTH] + [''] * (PastureParticipation.LENGTH - len(mp_value))
        return PastureParticipation(mp_value[PastureParticipation.INDEX_INDEX],
                                    mp_value[PastureParticipation.INDEX_GROVE_IGNS],
                                    mp_value[PastureParticipation.INDEX_MULE_IGNS],
                                    mp_value[PastureParticipation.INDEX_NAME],
                                    mp_value[PastureParticipation.INDEX_DISCORD_MENTION])


def get_unsorted_pasture_participation():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_PASTURE_PARTICIPATION).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    return list(map(lambda mp_value: PastureParticipation.from_sheets_value(mp_value), values))


def insert_weekly_participation_columns(header: str):
    insert_column_body = {"requests": [{"insertDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_PASTURE_PARTICIPATION,
                  "dimension": "COLUMNS",
                  "startIndex": 9,
                  "endIndex": 12},
        "inheritFromBefore": False
    }}]}

    week_header_format = {"requests": [{"mergeCells": {
        "mergeType": 'MERGE_COLUMNS',
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_PASTURE_PARTICIPATION,
                  "startColumnIndex": 9,
                  "endColumnIndex": 12,
                  "startRowIndex": 0,
                  "endRowIndex": 1},
    }}]}

    try:
        sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        body=insert_column_body).execute()

        sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        body=week_header_format).execute()

        body = {'values': [[header]]}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK_HEADER,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

        body = {'values': [['Mule Count', 'Culvert Average', 'Flag Race Average']]}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK_SUBHEADER,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


INDEX_MULE_COUNT = 0
INDEX_MULE_CULVERT = 1
INDEX_MULE_FLAG = 2


def update_weekly_participation(participations: list[list[int]]):
    try:
        body = {'values': participations}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error
