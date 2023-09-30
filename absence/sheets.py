from __future__ import print_function

from googleapiclient.errors import HttpError

import config
from utils import sheets


class Absence:
    LENGTH = 3

    INDEX_USER_ID = 0
    INDEX_EVENT_TYPE = 1
    INDEX_TIMESTAMP = 2

    def __init__(self, bosses_value):
        self.user_id = bosses_value[Absence.INDEX_USER_ID]
        self.event_type = bosses_value[Absence.INDEX_EVENT_TYPE]
        self.timestamp = bosses_value[Absence.INDEX_TIMESTAMP]

    def to_sheets_value(self):
        return [str(self.user_id), str(self.event_type), str(self.timestamp)]


class AbsenceSheets:
    SPREADSHEET_DISCORD_DATA = config.DISCORD_DATA_SPREADSHEET_ID
    SHEET_DISCORD_DATA_ABSENCES = config.DISCORD_DATA_SHEET_ID_ABSENCES
    RANGE_ABSENCES = 'Absences!A2:C'

    def __init__(self):
        self.__absences = self.__get_absences()

    @property
    def absences(self):
        return self.__absences

    @staticmethod
    def __get_absences():
        result = sheets.get_service().spreadsheets().values().get(spreadsheetId=AbsenceSheets.SPREADSHEET_DISCORD_DATA,
                                                                  range=AbsenceSheets.RANGE_ABSENCES).execute()
        absences_values = result.get('values', [])
        return list(map(lambda absences_value: Absence(absences_value), absences_values))

    def update_absences(self, new_sheets_absences: list[Absence]):
        def absence_to_sheets_values(sheets_absence: Absence):
            return sheets_absence.to_sheets_value()

        body = {'values': list(map(absence_to_sheets_values, new_sheets_absences))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=self.SPREADSHEET_DISCORD_DATA,
                                                            range=self.RANGE_ABSENCES, valueInputOption="RAW",
                                                            body=body).execute()
        self.__absences = new_sheets_absences

    def delete_absence(self, delete_sheets_absences: Absence):
        delete_index = 0
        for sheets_absence in self.__absences:
            if sheets_absence.user_id == delete_sheets_absences.user_id:
                # Found the entry
                break
            delete_index += 1

        if delete_index >= len(self.__absences):
            # Cannot find delete_member in sheets_members_list
            return

        delete_body = {"requests": [{"deleteDimension": {
            "range": {"sheetId": self.SHEET_DISCORD_DATA_ABSENCES, "dimension": "ROWS", "startIndex": delete_index + 1,
                      # Offset by 1 due to header row
                      "endIndex": delete_index + 2}}}]}
        try:
            sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=self.SPREADSHEET_DISCORD_DATA,
                                                            body=delete_body).execute()

            deleted_sheets_absence = self.__absences[delete_index]
            print(deleted_sheets_absence)

            # Remove deleted member from members list
            self.__absences = self.__absences[0:delete_index] + self.__absences[delete_index + 1:]

            return deleted_sheets_absence

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error
