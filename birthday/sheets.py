from __future__ import print_function

from datetime import datetime, timezone, timedelta

from googleapiclient.errors import HttpError

import config
from utils import sheets
from utils.constants import ONE_DAY_IN_SECONDS


class Birthday:
    LENGTH = 3

    INDEX_USER_ID = 0
    INDEX_BIRTHDAY_STR = 1
    INDEX_RESET_OFFSET = 2

    def __init__(self, user_id: int, birthday_str: str, reset_offset: float):
        self.user_id = user_id
        self.birthday_str = birthday_str
        self.reset_offset = reset_offset

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_sheets_value(birthdays_value):
        return Birthday(int(birthdays_value[Birthday.INDEX_USER_ID]),
                        birthdays_value[Birthday.INDEX_BIRTHDAY_STR],
                        float(birthdays_value[Birthday.INDEX_RESET_OFFSET]))

    def to_sheets_value(self):
        return [str(self.user_id), str(self.birthday_str), str(self.reset_offset)]

    @staticmethod
    def get_next_birthday(birthday_str: str, reset_offset: float):
        now = datetime.now()
        next_birthday = datetime.strptime(birthday_str, '%m-%d').replace(year=now.year,
                                                                         tzinfo=timezone.utc)
        next_birthday = next_birthday + timedelta(hours=reset_offset)
        if next_birthday.timestamp() - now.timestamp() < -1 * ONE_DAY_IN_SECONDS:
            # If it is less than 24 hours after the start of the birthday, return this year's birthday
            next_birthday = next_birthday.replace(year=next_birthday.year + 1)
        return next_birthday


class BirthdaySheets:
    RANGE_BIRTHDAYS = 'Birthdays!A2:C'

    def __init__(self):
        self.__birthdays = self.__get_birthdays()

    @property
    def birthdays(self):
        return self.__birthdays

    @staticmethod
    def __get_birthdays():
        result = sheets.get_service().spreadsheets().values().get(
            spreadsheetId=config.MEMBER_ACTIVITY_SPREADSHEET_ID,
            range=BirthdaySheets.RANGE_BIRTHDAYS).execute()
        birthdays_values = result.get('values', [])
        return list(map(lambda birthdays_value: Birthday.from_sheets_value(birthdays_value), birthdays_values))

    def append_birthday(self, new_sheets_birthday: Birthday):
        body = {'values': [new_sheets_birthday.to_sheets_value()]}
        sheets.get_service().spreadsheets().values().append(spreadsheetId=config.MEMBER_ACTIVITY_SPREADSHEET_ID,
                                                            range=self.RANGE_BIRTHDAYS, valueInputOption="RAW",
                                                            body=body).execute()
        self.__birthdays.append(new_sheets_birthday)

    def update_birthdays(self, new_sheets_birthdays: list[Birthday]):

        def birthday_to_sheets_values(sheets_birthday: Birthday):
            return sheets_birthday.to_sheets_value()

        body = {'values': list(map(birthday_to_sheets_values, new_sheets_birthdays))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=config.MEMBER_ACTIVITY_SPREADSHEET_ID,
                                                            range=self.RANGE_BIRTHDAYS, valueInputOption="RAW",
                                                            body=body).execute()
        self.__birthdays = new_sheets_birthdays

    def delete_user_birthday(self, user_id: int):
        delete_index = 0
        for sheets_birthday in self.__birthdays:
            if sheets_birthday.user_id == user_id:
                # Found the entry
                break
            delete_index += 1

        if delete_index >= len(self.__birthdays):
            # Cannot find delete_member in sheets_members_list
            return

        delete_body = {"requests": [{"deleteDimension": {
            "range": {"sheetId": config.MEMBER_ACTIVITY_SHEET_ID_BIRTHDAYS, "dimension": "ROWS",
                      "startIndex": delete_index + 1,
                      # Offset by 1 due to header row
                      "endIndex": delete_index + 2}}}]}
        try:
            sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=config.MEMBER_ACTIVITY_SPREADSHEET_ID,
                                                            body=delete_body).execute()

            deleted_sheets_birthday = self.__birthdays[delete_index]
            print(deleted_sheets_birthday)

            # Remove deleted member from members list
            self.__birthdays = self.__birthdays[0:delete_index] + self.__birthdays[delete_index + 1:]

            return deleted_sheets_birthday

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error
