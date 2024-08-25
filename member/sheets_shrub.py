from functools import reduce

from googleapiclient.errors import HttpError

import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_SHRUB_PARTICIPATION = 'Shrub Participation!A2:ZZZ'
RANGE_WEEK_HEADER = 'Shrub Participation!F1:G1'
RANGE_WEEK = 'Shrub Participation!F2:G'
WEEKLY_PARTICIPATION_COLUMN_INDEX = 5
WEEKLY_PARTICIPATION_COLUMNS = 2


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


class ShrubParticipation:
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
    def from_sheets_value(sp_value: list[str]):
        sp_value = sp_value[:ShrubParticipation.LENGTH] + [''] * (ShrubParticipation.LENGTH - len(sp_value))
        return ShrubParticipation(sp_value[ShrubParticipation.INDEX_INDEX],
                                  sp_value[ShrubParticipation.INDEX_GROVE_IGNS],
                                  sp_value[ShrubParticipation.INDEX_MULE_IGNS],
                                  sp_value[ShrubParticipation.INDEX_NAME],
                                  sp_value[ShrubParticipation.INDEX_DISCORD_MENTION])


def get_unsorted_shrub_participation():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_SHRUB_PARTICIPATION).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    return list(map(lambda sp_value: ShrubParticipation.from_sheets_value(sp_value), values))


def insert_weekly_participation_columns(header: str):
    insert_column_body = {"requests": [{"insertDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_SHRUB_PARTICIPATION,
                  "dimension": "COLUMNS",
                  "startIndex": WEEKLY_PARTICIPATION_COLUMN_INDEX,
                  "endIndex": WEEKLY_PARTICIPATION_COLUMN_INDEX + WEEKLY_PARTICIPATION_COLUMNS},
        "inheritFromBefore": False
    }}]}

    try:
        sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        body=insert_column_body).execute()

        body = {'values': [[header, 'Details']]}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK_HEADER,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


class WeeklyParticipation:
    def __init__(self, culvert_point_score: int):
        self.culvert_point_score = culvert_point_score
        self.mule_igns = []
        self.culvert = 0
        self.flag = 0

    def __str__(self):
        return str([self.mule_igns, self.culvert, self.flag])

    def __repr__(self):
        return self.__str__()

    def add(self, mule_ign, culvert, flag):
        self.mule_igns.append(mule_ign)
        self.culvert += culvert
        self.flag += flag

    def __count(self):
        return len(self.mule_igns)

    def __points(self):
        if self.__count() == 0:
            return 0
        points = self.__count() * -2
        points += self.__culvert_points()
        points += self.__flag_points()
        return points

    def __culvert_points(self):
        return int(self.culvert / self.culvert_point_score)

    def __flag_points(self):
        if self.__count() == 0:
            return 0
        return min(int(self.flag / 50), self.__count())

    def to_sheets_value(self):
        if self.__count() == 0:
            return ['', '']
        return [self.__points(), (f'Count: {self.__count()} ({self.__count() * -2})\n'
                                  f'Culvert: {self.culvert} ({self.__culvert_points()})\n'
                                  f'Flag Race: {self.flag} ({self.__flag_points()})\n'
                                  f'\n'
                                  f'{reduce(lambda acc, val: acc + (chr(10) if acc else "") + val, self.mule_igns)}')]


def update_weekly_participation(wp_list: list[WeeklyParticipation]):
    try:
        body = {'values': list(map(lambda wp: wp.to_sheets_value(), wp_list))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error
