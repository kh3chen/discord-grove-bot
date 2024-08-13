from __future__ import print_function

from datetime import datetime, timezone, timedelta
from enum import Enum

from googleapiclient.errors import HttpError

import config
from utils import sheets


class Boss:
    LENGTH = 5

    INDEX_BOSS_NAME = 0
    INDEX_ROLE_COLOUR = 1
    INDEX_HUMAN_READABLE_NAME = 2
    INDEX_FORUM_CHANNEL_ID = 3
    INDEX_SIGN_UP_THREAD_ID = 4

    def __init__(self, bosses_value):
        bosses_value = bosses_value[:Boss.LENGTH] + [''] * (Boss.LENGTH - len(bosses_value))
        self.boss_name = bosses_value[Boss.INDEX_BOSS_NAME]
        self._role_colour = bosses_value[Boss.INDEX_ROLE_COLOUR]
        self.human_readable_name = bosses_value[Boss.INDEX_HUMAN_READABLE_NAME]
        self.forum_channel_id = bosses_value[Boss.INDEX_FORUM_CHANNEL_ID]
        self.sign_up_thread_id = bosses_value[Boss.INDEX_SIGN_UP_THREAD_ID]
        self.difficulties = {}

    def get_role_colour(self):
        return int(self._role_colour, 16)

    def __str__(self):
        return str(
            [str(self.boss_name), str(self._role_colour), str(self.human_readable_name), str(self.forum_channel_id),
             str(self.sign_up_thread_id), str(self.difficulties)])

    def __repr__(self):
        return self.__str__()


class Difficulty:
    LENGTH = 4

    INDEX_BOSS_NAME = 0
    INDEX_DIFFICULTY = 1
    INDEX_LFG_ROLE_ID = 2
    INDEX_FILL_ROLE_ID = 3

    def __init__(self, difficulties_value):
        difficulties_value = difficulties_value[:Boss.LENGTH] + [''] * (Boss.LENGTH - len(difficulties_value))
        self.difficulty = difficulties_value[Difficulty.INDEX_DIFFICULTY]
        self.lfg_role_id = difficulties_value[Difficulty.INDEX_LFG_ROLE_ID]
        self.fill_role_id = difficulties_value[Difficulty.INDEX_FILL_ROLE_ID]

    def __str__(self):
        return str([str(self.lfg_role_id), str(self.fill_role_id)])

    def __repr__(self):
        return self.__str__()


class Party:
    LENGTH = 14

    INDEX_ROLE_ID = 0
    INDEX_BOSS_NAME = 1
    INDEX_DIFFICULTY = 2
    INDEX_PARTY_NUMBER = 3
    INDEX_STATUS = 4
    INDEX_MEMBER_COUNT = 5
    INDEX_WEEKDAY = 6
    INDEX_HOUR = 7
    INDEX_MINUTE = 8
    INDEX_PARTY_THREAD_ID = 9
    INDEX_PARTY_MESSAGE_ID = 10
    INDEX_BOSS_LIST_MESSAGE_ID = 11
    INDEX_BOSS_LIST_DECORATOR_ID = 12
    INDEX_CHECK_IN_MESSAGE_ID = 13

    class PartyStatus(Enum):
        new = "new"
        open = "open"
        exclusive = "exclusive"
        lfg = "lfg"
        fill = "fill"
        retired = "retired"

    class Weekday(Enum):
        mon = 1
        tue = 2
        wed = 3
        thu = 4
        fri = 5
        sat = 6
        sun = 7

    def __init__(self,
                 role_id,
                 boss_name,
                 difficulty,
                 party_number,
                 status,
                 member_count,
                 weekday,
                 hour,
                 minute,
                 party_thread_id,
                 party_message_id,
                 boss_list_message_id,
                 boss_list_decorator_id,
                 check_in_message_id):
        self.role_id = str(role_id)
        self.boss_name = str(boss_name)
        self.difficulty = str(difficulty)
        self.party_number = str(party_number)
        self.status = Party.PartyStatus[status or Party.PartyStatus.new.value]
        self.member_count = str(member_count)
        self.weekday = str(weekday)
        self.hour = str(hour)
        self.minute = str(minute)
        self.party_thread_id = str(party_thread_id)
        self.party_message_id = str(party_message_id)
        self.boss_list_message_id = str(boss_list_message_id)
        self.boss_list_decorator_id = str(boss_list_decorator_id)
        self.check_in_message_id = str(check_in_message_id)

    @staticmethod
    def from_sheets_value(party_value: list[str]):
        party_value = party_value[:Party.LENGTH] + [''] * (Party.LENGTH - len(party_value))
        return Party(party_value[Party.INDEX_ROLE_ID],
                     party_value[Party.INDEX_BOSS_NAME],
                     party_value[Party.INDEX_DIFFICULTY],
                     party_value[Party.INDEX_PARTY_NUMBER],
                     party_value[Party.INDEX_STATUS],
                     party_value[Party.INDEX_MEMBER_COUNT],
                     party_value[Party.INDEX_WEEKDAY],
                     party_value[Party.INDEX_HOUR],
                     party_value[Party.INDEX_MINUTE],
                     party_value[Party.INDEX_PARTY_THREAD_ID],
                     party_value[Party.INDEX_PARTY_MESSAGE_ID],
                     party_value[Party.INDEX_BOSS_LIST_MESSAGE_ID],
                     party_value[Party.INDEX_BOSS_LIST_DECORATOR_ID],
                     party_value[Party.INDEX_CHECK_IN_MESSAGE_ID])

    @staticmethod
    def new_party(role_id: int, boss_name: str, difficulty: str, party_number: int):
        new_sheets_party = Party.from_sheets_value([])
        new_sheets_party.role_id = str(role_id)
        new_sheets_party.boss_name = boss_name
        new_sheets_party.difficulty = difficulty
        new_sheets_party.party_number = str(party_number)
        new_sheets_party.status = Party.PartyStatus.new
        new_sheets_party.member_count = "0"
        return new_sheets_party

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def get_mention(self):
        return f'<@&{self.role_id}>'

    def to_sheets_value(self):
        return [str(self.role_id),
                str(self.boss_name),
                str(self.difficulty),
                str(self.party_number),
                self.status.value,
                str(self.member_count),
                str(self.weekday),
                str(self.hour),
                str(self.minute),
                str(self.party_thread_id),
                str(self.party_message_id),
                str(self.boss_list_message_id),
                str(self.boss_list_decorator_id),
                str(self.check_in_message_id)]

    def next_scheduled_time(self):
        if not self.weekday or not self.hour or not self.minute:
            return ''

        weekday = Party.Weekday[self.weekday].value
        hour = int(self.hour)
        minute = int(self.minute)
        now = datetime.now(timezone.utc)
        if now.isoweekday() == weekday:
            if now.hour > hour or now.hour == hour and now.minute > minute:
                next_time = (now + timedelta(days=7)).replace(hour=hour, minute=minute, second=0)
                return str(int(datetime.timestamp(next_time)))
            else:
                next_time = now.replace(hour=hour, minute=minute, second=0)
                return str(int(datetime.timestamp(next_time)))
        else:
            next_time = (now + timedelta(days=(weekday - now.isoweekday()) % 7)).replace(hour=hour, minute=minute,
                                                                                         second=0)
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
    def from_sheets_value(member_value: list[str]):
        member_value = member_value[:Member.LENGTH] + [''] * (Member.LENGTH - len(member_value))
        return Member(member_value[Member.INDEX_BOSS_NAME], member_value[Member.INDEX_PARTY_NUMBER],
                      member_value[Member.INDEX_PARTY_ROLE_ID], member_value[Member.INDEX_USER_ID],
                      member_value[Member.INDEX_JOB])

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [str(self.boss_name), str(self.party_number), str(self.party_role_id), str(self.user_id), str(self.job)]


class NoShow:
    LENGTH = 5

    INDEX_TIMESTAMP = 0
    INDEX_USER_ID = 1
    INDEX_PARTY_ROLE_ID = 2
    INDEX_BOSS_NAME = 3
    INDEX_PARTY_NUMBER = 4

    def __init__(self,
                 timestamp: int,
                 user_id: str,
                 party_role_id: str,
                 boss_name: str,
                 party_number: str):
        self.timestamp = timestamp
        self.user_id = user_id
        self.party_role_id = party_role_id
        self.boss_name = boss_name
        self.party_number = party_number

    @staticmethod
    def from_sheets_value(no_show_value: list[str]):
        no_show_value = no_show_value[:NoShow.LENGTH] + [''] * (NoShow.LENGTH - len(no_show_value))
        return NoShow(int(no_show_value[NoShow.INDEX_TIMESTAMP]),
                      no_show_value[NoShow.INDEX_USER_ID],
                      no_show_value[NoShow.INDEX_PARTY_ROLE_ID],
                      no_show_value[NoShow.INDEX_BOSS_NAME],
                      no_show_value[NoShow.INDEX_PARTY_NUMBER])

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [str(self.timestamp),
                str(self.user_id),
                str(self.party_role_id),
                str(self.boss_name),
                str(self.party_number)]


class BossingSheets:
    SPREADSHEET_BOSS_PARTIES = config.BOSS_PARTIES_SPREADSHEET_ID  # The ID of the bossing parties spreadsheet
    SHEET_BOSS_PARTIES_MEMBERS = config.BOSS_PARTIES_SHEET_ID_MEMBERS  # The ID of the Members sheet
    RANGE_BOSSES = 'Bosses!A2:E'
    RANGE_DIFFICULTIES = 'Difficulties!A2:D'
    RANGE_PARTIES = 'Parties!A2:N'
    RANGE_MEMBERS = 'Members!A2:E'
    RANGE_NO_SHOWS = 'No Shows!A2:E'

    @staticmethod
    def __get_bosses_dict():
        result = sheets.get_service().spreadsheets().values().get(spreadsheetId=BossingSheets.SPREADSHEET_BOSS_PARTIES,
                                                                  range=BossingSheets.RANGE_BOSSES).execute()
        bosses_values = result.get('values', [])
        bosses = {}
        for bosses_value in bosses_values:
            bosses[bosses_value[Boss.INDEX_BOSS_NAME]] = Boss(bosses_value)

        result = sheets.get_service().spreadsheets().values().get(spreadsheetId=BossingSheets.SPREADSHEET_BOSS_PARTIES,
                                                                  range=BossingSheets.RANGE_DIFFICULTIES).execute()
        difficulties_values = result.get('values', [])
        for difficulties_value in difficulties_values:
            difficulty = Difficulty(difficulties_value)
            bosses[difficulties_value[Difficulty.INDEX_BOSS_NAME]].difficulties[difficulty.difficulty] = difficulty

        return bosses

    @staticmethod
    def __get_parties():
        result = sheets.get_service().spreadsheets().values().get(spreadsheetId=BossingSheets.SPREADSHEET_BOSS_PARTIES,
                                                                  range=BossingSheets.RANGE_PARTIES).execute()
        party_values = result.get('values', [])
        return list(map(lambda party_value: Party.from_sheets_value(party_value), party_values))

    @staticmethod
    def __get_members():
        result = sheets.get_service().spreadsheets().values().get(spreadsheetId=BossingSheets.SPREADSHEET_BOSS_PARTIES,
                                                                  range=BossingSheets.RANGE_MEMBERS).execute()
        members_values = result.get('values', [])
        return list(map(lambda members_value: Member.from_sheets_value(members_value), members_values))

    def __get_members_dict(self):
        # Key of the following dictionaries is the bossing party role ID
        members_dict = {}
        for sheets_party in self.__parties:
            members_dict[sheets_party.role_id] = []

        for sheets_member in self.__members:
            try:
                members_dict[sheets_member.party_role_id].append(sheets_member)
            except KeyError:
                # The party ID doesn't exist
                continue

        return members_dict

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print('Creating the object')
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__bosses_dict = None
        self.__parties = None
        self.__members = None
        self.__members_dict = None
        self.sync_data()

    def sync_data(self):
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

    def update_parties(self, new_sheets_parties: list[Party], added_parties=None):
        if added_parties is None:
            added_parties = []

        def party_to_sheets_values(sheets_party: Party):
            return sheets_party.to_sheets_value()

        body = {'values': list(map(party_to_sheets_values, new_sheets_parties))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=self.SPREADSHEET_BOSS_PARTIES,
                                                            range=self.RANGE_PARTIES, valueInputOption="RAW",
                                                            body=body).execute()
        self.__parties = new_sheets_parties

        for added_party in added_parties:
            self.__members_dict[added_party.role_id] = []

    def append_members(self, new_sheets_members: list[Member]):
        def member_to_sheets_values(sheets_member: Member):
            return sheets_member.to_sheets_value()

        body = {'values': list(map(member_to_sheets_values, new_sheets_members))}
        sheets.get_service().spreadsheets().values().append(spreadsheetId=self.SPREADSHEET_BOSS_PARTIES,
                                                            range=self.RANGE_MEMBERS, valueInputOption="RAW",
                                                            body=body).execute()

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

        delete_body = {"requests": [{"deleteDimension": {
            "range": {"sheetId": self.SHEET_BOSS_PARTIES_MEMBERS, "dimension": "ROWS", "startIndex": delete_index + 1,
                      # Due to header row
                      "endIndex": delete_index + 2}}}]}
        try:
            sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=self.SPREADSHEET_BOSS_PARTIES,
                                                            body=delete_body).execute()

            deleted_sheets_member = self.__members[delete_index]
            print(deleted_sheets_member)

            # Remove deleted member from members list
            self.__members = self.__members[0:delete_index] + self.__members[delete_index + 1:]

            # Remove deleted member from members dict
            for sheets_member in self.__members_dict[deleted_sheets_member.party_role_id]:
                if sheets_member.user_id == deleted_sheets_member.user_id and sheets_member.job == deleted_sheets_member.job:
                    self.__members_dict[deleted_sheets_member.party_role_id].remove(sheets_member)
                    break

            return deleted_sheets_member

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error

    def append_no_shows(self, no_shows: list[NoShow]):
        def no_show_to_sheets_values(no_show: NoShow):
            return no_show.to_sheets_value()

        body = {'values': list(map(no_show_to_sheets_values, no_shows))}
        sheets.get_service().spreadsheets().values().append(spreadsheetId=self.SPREADSHEET_BOSS_PARTIES,
                                                            range=self.RANGE_NO_SHOWS, valueInputOption="RAW",
                                                            body=body).execute()
