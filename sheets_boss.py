from __future__ import print_function

from datetime import datetime, timezone, timedelta
from enum import Enum

import config
from sheets import __get_service

SPREADSHEET_BOSS_PARTIES = config.BOSS_PARTIES_SPREADSHEET_ID  # The ID of the boss parties spreadsheet
SHEET_BOSS_PARTIES_MEMBERS = config.BOSS_PARTIES_SHEET_ID_MEMBERS  # The ID of the Members sheet
RANGE_BOSSES = 'Bosses!A2:D'
RANGE_PARTIES = 'Parties!A2:L'
RANGE_MEMBERS = 'Members!A2:C'


class SheetsBoss:
    LENGTH = 4

    INDEX_BOSS_NAME = 0
    INDEX_ROLE_COLOUR = 1
    INDEX_HUMAN_READABLE_NAME = 2
    INDEX_FORUM_CHANNEL_ID = 3

    def __init__(self, bosses_value):
        bosses_value = bosses_value[:SheetsParty.LENGTH] + [''] * (SheetsParty.LENGTH - len(bosses_value))
        self.boss_name = bosses_value[SheetsBoss.INDEX_BOSS_NAME]
        self._role_colour = bosses_value[SheetsBoss.INDEX_ROLE_COLOUR]
        self.human_readable_name = bosses_value[SheetsBoss.INDEX_HUMAN_READABLE_NAME]
        self.forum_channel_id = bosses_value[SheetsBoss.INDEX_FORUM_CHANNEL_ID]

    def get_role_colour(self):
        return int(self._role_colour, 16)


class SheetsParty:
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
        open = 1
        full = 2
        exclusive = 3
        fill = 4
        retired = 5

    class Weekday(Enum):
        mon = 1
        tue = 2
        wed = 3
        thu = 4
        fri = 5
        sat = 6
        sun = 7

    def __init__(self, parties_value: list[str]):
        parties_value = parties_value[:SheetsParty.LENGTH] + [''] * (SheetsParty.LENGTH - len(parties_value))
        self.role_id = parties_value[SheetsParty.INDEX_ROLE_ID]
        self.boss_name = parties_value[SheetsParty.INDEX_BOSS_NAME]
        self.party_number = parties_value[SheetsParty.INDEX_PARTY_NUMBER]
        self.status = parties_value[SheetsParty.INDEX_STATUS]
        self.member_count = parties_value[SheetsParty.INDEX_MEMBER_COUNT]
        self.weekday = parties_value[SheetsParty.INDEX_WEEKDAY]
        self.hour = parties_value[SheetsParty.INDEX_HOUR]
        self.minute = parties_value[SheetsParty.INDEX_MINUTE]
        self.party_thread_id = parties_value[SheetsParty.INDEX_PARTY_THREAD_ID]
        self.party_message_id = parties_value[SheetsParty.INDEX_PARTY_MESSAGE_ID]
        self.boss_list_message_id = parties_value[SheetsParty.INDEX_BOSS_LIST_MESSAGE_ID]
        self.boss_list_decorator_id = parties_value[SheetsParty.INDEX_BOSS_LIST_DECORATOR_ID]

    def __str__(self):
        return str(self.to_sheets_values())

    def __repr__(self):
        return self.__str__()

    def to_sheets_values(self):
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

        weekday = SheetsParty.Weekday[self.weekday].value
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


class SheetsMember:
    LENGTH = 3

    INDEX_USER_ID = 0
    INDEX_PARTY_ROLE_ID = 1
    INDEX_JOB = 2

    def __init__(self, members_value: list[str]):
        members_value = members_value[:SheetsMember.LENGTH] + [''] * (SheetsMember.LENGTH - len(members_value))
        self.user_id = members_value[SheetsMember.INDEX_USER_ID]
        self.party_role_id = members_value[SheetsMember.INDEX_PARTY_ROLE_ID]
        self.job = members_value[SheetsMember.INDEX_JOB]

    def __str__(self):
        return str(self.to_sheets_values())

    def __repr__(self):
        return self.__str__()

    def to_sheets_values(self):
        return [
            str(self.user_id),
            str(self.party_role_id),
            str(self.job)
        ]


def get_bosses_dict():
    result = __get_service().spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                         range=RANGE_BOSSES).execute()
    bosses_values = result.get('values', [])
    bosses = {}
    for bosses_value in bosses_values:
        bosses[bosses_value[0]] = SheetsBoss(bosses_value)
    return bosses


def get_parties_list():
    result = __get_service().spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                         range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    return list(map(lambda parties_value: SheetsParty(parties_value), parties_values))


def update_parties(sheets_parties: list[SheetsParty]):
    def party_to_sheets_values(sheets_party: SheetsParty):
        return sheets_party.to_sheets_values()

    body = {
        'values': list(map(party_to_sheets_values, sheets_parties))
    }
    return __get_service().spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                                          valueInputOption="RAW", body=body).execute()


def get_members_list():
    result = __get_service().spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                         range=RANGE_MEMBERS).execute()
    members_values = result.get('values', [])
    return list(map(lambda members_value: SheetsMember(members_value), members_values))


def append_members(new_sheets_members: list[SheetsMember]):
    def member_to_sheets_values(sheets_member: SheetsMember):
        return sheets_member.to_sheets_values()

    body = {
        'values': list(map(member_to_sheets_values, new_sheets_members))
    }
    return __get_service().spreadsheets().values().append(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
                                                          valueInputOption="RAW", body=body).execute()


def delete_member(delete_index: int):
    delete_body = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": SHEET_BOSS_PARTIES_MEMBERS,
                        "dimension": "ROWS",
                        "startIndex": delete_index,
                        "endIndex": delete_index + 1
                    }
                }
            }
        ]
    }
    return __get_service().spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_BOSS_PARTIES, body=delete_body).execute()
