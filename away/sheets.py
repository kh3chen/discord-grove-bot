from __future__ import print_function

from googleapiclient.errors import HttpError

import config
from utils import sheets


class Away:
    LENGTH = 3

    INDEX_USER_ID = 0
    INDEX_EVENT_TYPE = 1
    INDEX_TIMESTAMP = 2

    def __init__(self, bosses_value):
        self.user_id = bosses_value[Away.INDEX_USER_ID]
        self.event_type = bosses_value[Away.INDEX_EVENT_TYPE]
        self.timestamp = bosses_value[Away.INDEX_TIMESTAMP]

    def to_sheets_value(self):
        return [str(self.user_id), str(self.event_type), str(self.timestamp)]


class AwaySheets:
    SPREADSHEET_DISCORD_DATA = config.DISCORD_DATA_SPREADSHEET_ID
    SHEET_DISCORD_DATA_AWAY = config.DISCORD_DATA_SHEET_ID_AWAYS
    RANGE_AWAY = 'Aways!A2:C'

    def __init__(self):
        self.__aways = self.__get_aways()

    @staticmethod
    def __get_aways():
        result = sheets.get_service().spreadsheets().values().get(spreadsheetId=AwaySheets.SPREADSHEET_DISCORD_DATA,
                                                                  range=AwaySheets.RANGE_AWAY).execute()
        aways_values = result.get('values', [])
        return list(map(lambda aways_value: Away(aways_value), aways_values))

    def update_aways(self, new_sheets_aways: list[Away]):
        def away_to_sheets_values(sheets_away: Away):
            return sheets_away.to_sheets_value()

        body = {'values': list(map(away_to_sheets_values, new_sheets_aways))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=self.SPREADSHEET_DISCORD_DATA,
                                                            range=self.RANGE_AWAY, valueInputOption="RAW",
                                                            body=body).execute()
        self.__aways = new_sheets_aways

    def delete_away(self, delete_sheets_away: Away):
        delete_index = 0
        for sheets_away in self.__aways:
            if sheets_away.user_id == delete_sheets_away.user_id:
                # Found the entry
                break
            delete_index += 1

        if delete_index >= len(self.__aways):
            # Cannot find delete_member in sheets_members_list
            return

        delete_body = {"requests": [{"deleteDimension": {
            "range": {"sheetId": self.SHEET_DISCORD_DATA_AWAY, "dimension": "ROWS", "startIndex": delete_index + 1,
                      # Offset by 1 due to header row
                      "endIndex": delete_index + 2}}}]}
        try:
            sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=self.SPREADSHEET_DISCORD_DATA,
                                                            body=delete_body).execute()

            deleted_sheets_away = self.__aways[delete_index]
            print(deleted_sheets_away)

            # Remove deleted member from members list
            self.__aways = self.__aways[0:delete_index] + self.__aways[delete_index + 1:]

            return deleted_sheets_away

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error
