from __future__ import print_function

from datetime import datetime, timezone, timedelta
from enum import Enum

from googleapiclient.errors import HttpError

import config
import sheets


class Boss:
    LENGTH = 5

    INDEX_BOSS_NAME = 0
    INDEX_ROLE_COLOUR = 1
    INDEX_HUMAN_READABLE_NAME = 2
    INDEX_FORUM_CHANNEL_ID = 3
    INDEX_FILL_ROLE_ID = 4

    def __init__(self, bosses_value):
        bosses_value = bosses_value[:Boss.LENGTH] + [''] * (
                Boss.LENGTH - len(bosses_value))
        self.boss_name = bosses_value[Boss.INDEX_BOSS_NAME]
        self._role_colour = bosses_value[Boss.INDEX_ROLE_COLOUR]
        self.human_readable_name = bosses_value[Boss.INDEX_HUMAN_READABLE_NAME]
        self.forum_channel_id = bosses_value[Boss.INDEX_FORUM_CHANNEL_ID]
        self.fill_role_id = bosses_value[Boss.INDEX_FILL_ROLE_ID]

    def get_role_colour(self):
        return int(self._role_colour, 16)


class Party:
    LENGTH = 12

    INDEX_ROLE_ID = 0
    INDEX_BOSS_NAME = 1
    INDEX_PARTY_NUMBER = 2
    INDEX_STATUS = 3
    INDEX_MEMBER_COUNT = 4
    INDEX_WEEKDAY = 5
    INDEX_HOUR = 6
    INDEX_MINUTE = 7
    INDEX_PARTY_THREAD_ID = 8
    INDEX_PARTY_MESSAGE_ID = 9
    INDEX_BOSS_LIST_MESSAGE_ID = 10
    INDEX_BOSS_LIST_DECORATOR_ID = 11

    class PartyStatus(Enum):
        new = 0
        open = 1
        exclusive = 2
        fill = 3
        retired = 4

    class Weekday(Enum):
        mon = 1
        tue = 2
        wed = 3
        thu = 4
        fri = 5
        sat = 6
        sun = 7

    def __init__(self, role_id, boss_name, party_number, status, member_count, weekday, hour, minute,
                 party_thread_id,
                 party_message_id, boss_list_message_id, boss_list_decorator_id):
        self.role_id = str(role_id)
        self.boss_name = str(boss_name)
        self.party_number = str(party_number)
        self.status = str(status)
        self.member_count = str(member_count)
        self.weekday = str(weekday)
        self.hour = str(hour)
        self.minute = str(minute)
        self.party_thread_id = str(party_thread_id)
        self.party_message_id = str(party_message_id)
        self.boss_list_message_id = str(boss_list_message_id)
        self.boss_list_decorator_id = str(boss_list_decorator_id)

    @staticmethod
    def from_sheets_value(parties_value: list[str]):
        parties_value = parties_value[:Party.LENGTH] + [''] * (
                Party.LENGTH - len(parties_value))
        return Party(parties_value[Party.INDEX_ROLE_ID],
                     parties_value[Party.INDEX_BOSS_NAME],
                     parties_value[Party.INDEX_PARTY_NUMBER],
                     parties_value[Party.INDEX_STATUS],
                     parties_value[Party.INDEX_MEMBER_COUNT],
                     parties_value[Party.INDEX_WEEKDAY],
                     parties_value[Party.INDEX_HOUR],
                     parties_value[Party.INDEX_MINUTE],
                     parties_value[Party.INDEX_PARTY_THREAD_ID],
                     parties_value[Party.INDEX_PARTY_MESSAGE_ID],
                     parties_value[Party.INDEX_BOSS_LIST_MESSAGE_ID],
                     parties_value[Party.INDEX_BOSS_LIST_DECORATOR_ID])

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [
            str(self.role_id),
            str(self.boss_name),
            str(self.party_number),
            str(self.status),
            str(self.member_count),
            str(self.weekday),
            str(self.hour),
            str(self.minute),
            str(self.party_thread_id),
            str(self.party_message_id),
            str(self.boss_list_message_id),
            str(self.boss_list_decorator_id)
        ]

    def next_scheduled_time(self):
        if not self.weekday or not self.hour or not self.minute:
            return ''

        weekday = Party.Weekday[self.weekday].value
        hour = int(self.hour)
        minute = int(self.minute)
        now = datetime.now(timezone.utc)
        if now.isoweekday() == self.weekday:
            if now.hour > hour or now.hour == hour and now.minute > minute:
                next_time = (now + timedelta(days=7)).replace(hour=hour, minute=minute)
                return str(int(datetime.timestamp(next_time)))
            else:
                next_time = now.replace(hour=hour, minute=minute)
                return str(int(datetime.timestamp(next_time)))
        else:
            next_time = (now + timedelta(days=(weekday - now.isoweekday()) % 7)).replace(hour=hour, minute=minute)
            return str(int(datetime.timestamp(next_time)))


class Member:
    LENGTH = 5

    INDEX_BOSS_NAME = 0
    INDEX_PARTY_NUMBER = 1
    INDEX_PARTY_ROLE_ID = 2
    INDEX_USER_ID = 3
    INDEX_JOB = 4

    def __init__(self, boss_name='', party_number='', party_role_id='', user_id='', job=''):
        self.boss_name = str(boss_name)
        self.party_number = str(party_number)
        self.party_role_id = str(party_role_id)
        self.user_id = str(user_id)
        self.job = str(job)

    @staticmethod
    def from_sheets_value(members_value: list[str]):
        members_value = members_value[:Member.LENGTH] + [''] * (
                Member.LENGTH - len(members_value))
        return Member(members_value[Member.INDEX_BOSS_NAME],
                      members_value[Member.INDEX_PARTY_NUMBER],
                      members_value[Member.INDEX_PARTY_ROLE_ID],
                      members_value[Member.INDEX_USER_ID],
                      members_value[Member.INDEX_JOB])

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [
            str(self.boss_name),
            str(self.party_number),
            str(self.party_role_id),
            str(self.user_id),
            str(self.job)
        ]


class SheetsBossing:
    SPREADSHEET_BOSS_PARTIES = config.BOSS_PARTIES_SPREADSHEET_ID  # The ID of the boss parties spreadsheet
    SHEET_BOSS_PARTIES_MEMBERS = config.BOSS_PARTIES_SHEET_ID_MEMBERS  # The ID of the Members sheet
    RANGE_BOSSES = 'Bosses!A2:E'
    RANGE_PARTIES = 'Parties!A2:L'
    RANGE_MEMBERS = 'Members!A2:E'

    @staticmethod
    def __get_bosses_dict():
        result = sheets.get_service().spreadsheets().values().get(
            spreadsheetId=SheetsBossing.SPREADSHEET_BOSS_PARTIES,
            range=SheetsBossing.RANGE_BOSSES).execute()
        bosses_values = result.get('values', [])
        bosses = {}
        for bosses_value in bosses_values:
            bosses[bosses_value[0]] = Boss(bosses_value)
        return bosses

    @staticmethod
    def __get_parties():
        result = sheets.get_service().spreadsheets().values().get(
            spreadsheetId=SheetsBossing.SPREADSHEET_BOSS_PARTIES,
            range=SheetsBossing.RANGE_PARTIES).execute()
        parties_values = result.get('values', [])
        return list(map(lambda parties_value: Party.from_sheets_value(parties_value), parties_values))

    @staticmethod
    def __get_members():
        result = sheets.get_service().spreadsheets().values().get(
            spreadsheetId=SheetsBossing.SPREADSHEET_BOSS_PARTIES,
            range=SheetsBossing.RANGE_MEMBERS).execute()
        members_values = result.get('values', [])
        return list(map(lambda members_value: Member.from_sheets_value(members_value), members_values))

    def __get_members_dict(self):
        # Key of the following dictionaries is the boss party role ID
        members_dict = {}
        for sheets_party in self.__parties:
            members_dict[sheets_party.role_id] = []

        for sheets_member in self.__members:
            members_dict[sheets_member.party_role_id].append(sheets_member)

        return members_dict

    def __init__(self):
        self.__bosses_dict = self.__get_bosses_dict()
        self.__parties = self.__get_parties()
        self.__members = self.__get_members()
        self.__members_dict = self.__get_members_dict()

    @property
    def bosses_dict(self):
        return self.__bosses_dict

    @property
    def parties(self):
        return self.__parties

    @property
    def members(self):
        return self.__members

    @property
    def members_dict(self):
        return self.__members_dict

    def get_boss_names(self):
        return list(self.__bosses_dict.keys())

    def update_parties(self, new_sheets_parties: list[Party], added_parties: list[Party] = []):
        def party_to_sheets_values(sheets_party: Party):
            return sheets_party.to_sheets_value()

        body = {
            'values': list(map(party_to_sheets_values, new_sheets_parties))
        }
        sheets.get_service().spreadsheets().values().update(spreadsheetId=self.SPREADSHEET_BOSS_PARTIES,
                                                            range=self.RANGE_PARTIES,
                                                            valueInputOption="RAW", body=body).execute()
        self.__parties = new_sheets_parties

        for added_party in added_parties:
            self.__members_dict[added_party.role_id] = []

    def append_members(self, new_sheets_members: list[Member]):
        def member_to_sheets_values(sheets_member: Member):
            return sheets_member.to_sheets_value()

        print(new_sheets_members)
        print(list(map(member_to_sheets_values, new_sheets_members)))

        body = {
            'values': list(map(member_to_sheets_values, new_sheets_members))
        }
        sheets.get_service().spreadsheets().values().append(spreadsheetId=self.SPREADSHEET_BOSS_PARTIES,
                                                            range=self.RANGE_MEMBERS,
                                                            valueInputOption="RAW", body=body).execute()

        self.__members += new_sheets_members
        for new_sheets_member in new_sheets_members:
            self.__members_dict[new_sheets_member.party_role_id].append(new_sheets_member)

    def delete_member(self, delete_sheets_member: Member):
        delete_index = 0
        for sheets_member in self.__members:
            if sheets_member.user_id == delete_sheets_member.user_id and sheets_member.party_role_id == delete_sheets_member.party_role_id and (
                    not delete_sheets_member.job or sheets_member.job == delete_sheets_member.job):
                # Found the entry
                break
            delete_index += 1

        if delete_index >= len(self.__members):
            # Cannot find delete_member in sheets_members_list
            return

        delete_body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": self.SHEET_BOSS_PARTIES_MEMBERS,
                            "dimension": "ROWS",
                            "startIndex": delete_index + 1,  # Due to header row
                            "endIndex": delete_index + 2
                        }
                    }
                }
            ]
        }
        try:
            sheets.get_service().spreadsheets().batchUpdate(
                spreadsheetId=self.SPREADSHEET_BOSS_PARTIES, body=delete_body).execute()

            deleted_sheets_member = self.__members[delete_index]
            self.__members = self.__members[0:delete_index] + self.__members[delete_index + 1:]
            for sheets_member in self.__members_dict[delete_sheets_member.party_role_id]:
                if sheets_member.user_id == delete_sheets_member.user_id and sheets_member.job == delete_sheets_member.job:
                    self.__members_dict[delete_sheets_member.party_role_id].remove(sheets_member)
                    break

            return deleted_sheets_member

        except HttpError as error:
            print(f"An error occurred: {error}")
            return error
