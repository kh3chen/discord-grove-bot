from __future__ import print_function

from enum import Enum

from googleapiclient.errors import HttpError

import config
from utils import sheets


class Absence:
    LENGTH = 3

    INDEX_TIMESTAMP = 0
    INDEX_USER_ID = 1
    INDEX_EVENT_TYPE = 2

    class Type(Enum):
        start = "start"
        end = "end"

    def __init__(self, timestamp: int, user_id: int, event_type: str):
        self.timestamp = timestamp
        self.user_id = user_id
        self.event_type = Absence.Type[event_type]

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_sheets_value(absences_value):
        return Absence(int(absences_value[Absence.INDEX_TIMESTAMP]),
                       int(absences_value[Absence.INDEX_USER_ID]),
                       absences_value[Absence.INDEX_EVENT_TYPE])

    def to_sheets_value(self):
        return [str(self.timestamp), str(self.user_id), self.event_type.value]


class AbsenceSheets:
    SPREADSHEET_GROVE_SUBMISSIONS = config.GROVE_SUBMISSIONS_SPREADSHEET_ID
    SHEET_GROVE_SUBMISSIONS_ABSENCES = config.GROVE_SUBMISSIONS_SHEET_ID_ABSENCES
    RANGE_ABSENCES = 'Absences!A2:C'

    def __init__(self):
        self.__absences = self.__get_absences()

    @property
    def absences(self):
        return self.__absences

    @staticmethod
    def __get_absences():
        result = sheets.get_service().spreadsheets().values().get(
            spreadsheetId=AbsenceSheets.SPREADSHEET_GROVE_SUBMISSIONS,
            range=AbsenceSheets.RANGE_ABSENCES).execute()
        absences_values = result.get('values', [])
        return list(map(lambda absences_value: Absence.from_sheets_value(absences_value), absences_values))

    def append_absences(self, *new_sheets_absences: Absence):
        def absence_to_sheets_values(sheets_absence: Absence):
            return sheets_absence.to_sheets_value()

        body = {'values': list(map(absence_to_sheets_values, new_sheets_absences))}
        sheets.get_service().spreadsheets().values().append(spreadsheetId=self.SPREADSHEET_GROVE_SUBMISSIONS,
                                                            range=self.RANGE_ABSENCES, valueInputOption="RAW",
                                                            body=body).execute()
        self.__absences += new_sheets_absences

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
            "range": {"sheetId": self.SHEET_GROVE_SUBMISSIONS_ABSENCES, "dimension": "ROWS",
                      "startIndex": delete_index + 1,
                      # Offset by 1 due to header row
                      "endIndex": delete_index + 2}}}]}
        try:
            sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=self.SPREADSHEET_GROVE_SUBMISSIONS,
                                                            body=delete_body).execute()

            deleted_sheets_absence = self.__absences[delete_index]
            print(deleted_sheets_absence)

            # Remove deleted member from members list
            self.__absences = self.__absences[0:delete_index] + self.__absences[delete_index + 1:]

            return deleted_sheets_absence

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error

    def delete_user_absences(self, user_id: int):
        delete_index = 0
        delete_count = 0
        for sheets_absence in self.__absences:
            if sheets_absence.user_id == user_id:
                # Found an entry
                delete_count += 1
            elif delete_count > 0:
                break
            else:
                delete_index += 1

        if delete_count == 0:
            # Nothing to delete
            return []

        delete_request = ({"deleteDimension": {
            "range": {"sheetId": self.SHEET_GROVE_SUBMISSIONS_ABSENCES, "dimension": "ROWS",
                      # Offset by 1 due to header row
                      "startIndex": delete_index + 1,
                      "endIndex": delete_index + delete_count + 1}}})

        delete_body = {"requests": delete_request}
        try:
            sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=self.SPREADSHEET_GROVE_SUBMISSIONS,
                                                            body=delete_body).execute()

            deleted_sheets_absences = self.__absences[delete_index:delete_index + delete_count]

            # Remove deleted member from members list
            self.__absences = self.__absences[0:delete_index] + self.__absences[delete_index + delete_count:]

            return deleted_sheets_absences

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error
