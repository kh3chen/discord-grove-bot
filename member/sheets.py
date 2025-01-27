import datetime
from enum import Enum

from googleapiclient.errors import HttpError

import config
from member.sheets_shrub import RANGE_SHRUB_PARTICIPATION, ShrubParticipation
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:G'
RANGE_MEMBER_PARTICIPATION = 'Weekly Participation!A2:ZZZ'
RANGE_WEEK_HEADER = 'Weekly Participation!N1'
RANGE_WEEK = 'Weekly Participation!N2:N'
RANGE_PAST_MEMBERS = 'Past Members'
RANGE_CUSTOM_IGN_MAPPING = 'Custom IGN Mapping!A2:B'
RANGE_TRACKING_DATA = 'Tracking Data'
RANGE_TRACKING_ERRORS = 'Tracking Errors'

ROLE_NAME_WARDEN = 'Warden'
ROLE_NAME_GUARDIAN = 'Guardian'
ROLE_NAME_SPIRIT = 'Spirit'
ROLE_NAME_TREE = 'Tree'
ROLE_NAME_SAPLING = 'Sapling'
ROLE_NAME_MOSS = 'Moss'
AVERAGE_THRESHOLD_SPIRIT = 20
CONTRIBUTION_THRESHOLD_SPIRIT = 300
CONTRIBUTION_THRESHOLD_TREE = 150


class Member:
    LENGTH = 4

    INDEX_DISCORD_MENTION = 0
    INDEX_VERIFIED_MAIN = 1
    INDEX_INTROED = 2
    INDEX_RANK = 3

    INTROED_TRUE = 'TRUE'
    INTROED_FALSE = 'FALSE'

    VERIFIED_MAIN_YES = 'Y'

    def __init__(self, discord_mention: str, verified_main: str, introed: str, rank: str):
        self.discord_mention = discord_mention
        self.introed = introed
        self.verified_main = verified_main
        self.rank = rank

    @staticmethod
    def from_sheets_value(members_value: list[str]):
        members_value = members_value[:Member.LENGTH] + [''] * (Member.LENGTH - len(members_value))
        return Member(members_value[Member.INDEX_DISCORD_MENTION],
                      members_value[Member.INDEX_VERIFIED_MAIN],
                      members_value[Member.INDEX_INTROED],
                      members_value[Member.INDEX_RANK])

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [self.discord_mention, self.verified_main, self.introed, self.rank]


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


def get_members():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return []

    return list(map(lambda value: Member.from_sheets_value(value), values))


def get_new_members():
    members = get_members()
    new_members = filter(lambda
                             member: member.discord_mention != '' and member.introed == Member.INTROED_FALSE and member.rank == ROLE_NAME_SAPLING,
                         members)
    return list(map(lambda member: member.discord_mention, new_members))


def update_introed_new_members():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])
    if not values:
        print('No data found.')
        return []

    members = list(map(lambda value: Member.from_sheets_value(value), values))
    for member in members:
        if member.discord_mention != '' and member.introed == Member.INTROED_FALSE:
            member.introed = Member.INTROED_TRUE

    body = {'values': list(map(lambda member: member.to_sheets_value(), members))}
    sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_MEMBERS, valueInputOption="USER_ENTERED",
                                                        body=body).execute()


class UpdateMemberRankResult(Enum):
    Success = 0
    NotFound = 1
    NotVerified = 2


def update_member_rank(member_id: int, grove_role_name: str):
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return UpdateMemberRankResult.NotFound

    members = list(map(lambda value: Member.from_sheets_value(value), values))
    try:
        member = next(member for member in members if
                      member.discord_mention == f'<@{member_id}>')
        if member.verified_main != Member.VERIFIED_MAIN_YES:
            return UpdateMemberRankResult.NotVerified
        member.rank = grove_role_name

        body = {'values': list(map(lambda member: member.to_sheets_value(), members))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_MEMBERS, valueInputOption="USER_ENTERED",
                                                            body=body).execute()
        return UpdateMemberRankResult.Success
    except StopIteration:
        return UpdateMemberRankResult.NotFound


def remove_member(member_id: int, reason: str = ''):
    service = sheets.get_service()

    # Delete Member Participation row
    member_participation = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                               range=RANGE_MEMBER_PARTICIPATION).execute()
    mp_values = member_participation.get('values', [])

    if not mp_values:
        print('No data found.')
        return

    remove_mp_value = None
    delete_mp_index = 1  # Offset by 1 due to header rows
    for mp_value in mp_values:
        if len(mp_value) > MemberParticipation.INDEX_DISCORD_MENTION and mp_value[MemberParticipation.INDEX_DISCORD_MENTION] == f'<@{member_id}>':
            # Found the entry
            remove_mp_value = mp_value
            break
        delete_mp_index += 1

    if delete_mp_index >= len(mp_values) or remove_mp_value is None:
        # Cannot find weekly participation value
        return

    # Append value to Past Members sheet
    past_member_value = [datetime.date.today().strftime('%Y-%m-%d'), reason] + remove_mp_value[1:]
    body = {'values': [past_member_value]}
    service.spreadsheets().values().append(spreadsheetId=config.MEMBER_TRACKING_SPREADSHEET_ID,
                                           range=RANGE_PAST_MEMBERS,
                                           valueInputOption="USER_ENTERED",
                                           body=body).execute()

    mp_delete_body = {"requests": [{"deleteDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_WEEKLY_PARTICIPATION, "dimension": "ROWS",
                  "startIndex": delete_mp_index,
                  "endIndex": delete_mp_index + 1}}}]}
    try:
        service.spreadsheets().batchUpdate(spreadsheetId=config.MEMBER_TRACKING_SPREADSHEET_ID,
                                           body=mp_delete_body).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error

    # Delete Shrub Participation row
    shrub_participation = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                                range=RANGE_SHRUB_PARTICIPATION).execute()
    sp_values = shrub_participation.get('values', [])

    if not sp_values:
        print('No data found.')
        return

    remove_sp_value = None
    delete_sp_index = 1  # Offset by 1 due to header rows
    for sp_value in sp_values:
        if len(sp_value) > ShrubParticipation.INDEX_DISCORD_MENTION and sp_value[ShrubParticipation.INDEX_DISCORD_MENTION] == f'<@{member_id}>':
            # Found the entry
            remove_sp_value = sp_value
            break
        delete_sp_index += 1

    if delete_sp_index >= len(sp_values) or remove_sp_value is None:
        # Cannot find weekly participation value
        return

    sp_delete_body = {"requests": [{"deleteDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_SHRUB_PARTICIPATION, "dimension": "ROWS",
                  "startIndex": delete_sp_index,
                  "endIndex": delete_sp_index + 1}}}]}
    try:
        service.spreadsheets().batchUpdate(spreadsheetId=config.MEMBER_TRACKING_SPREADSHEET_ID,
                                           body=sp_delete_body).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error

    # Delete Member List row
    member_list = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                      range=RANGE_MEMBERS).execute()
    member_values = member_list.get('values', [])

    if not member_values:
        print('No data found.')
        return

    member_list_delete_index = 2  # Offset by 2 due to header rows
    members = list(map(lambda value: Member.from_sheets_value(value), member_values))
    for member in members:
        if member.discord_mention == f'<@{member_id}>':
            # Found the entry
            break
        member_list_delete_index += 1

    if member_list_delete_index >= len(members):
        # Cannot find delete_member in sheets_members_list
        return

    member_delete_body = {"requests": [{"deleteDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_MEMBER_LIST, "dimension": "ROWS",
                  "startIndex": member_list_delete_index,
                  # Offset by 1 due to header row
                  "endIndex": member_list_delete_index + 1}}}]}
    try:
        service.spreadsheets().batchUpdate(spreadsheetId=config.MEMBER_TRACKING_SPREADSHEET_ID,
                                           body=member_delete_body).execute()
        return MemberParticipation.from_sheets_value(remove_mp_value)

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


class MemberParticipation:
    LENGTH = 12

    INDEX_INDEX = 0
    INDEX_GROVE_IGNS = 1
    INDEX_MULE_IGNS = 2
    INDEX_NAME = 3
    INDEX_SCORE = 4
    INDEX_DISCORD_MENTION = 5
    INDEX_INTROED = 6
    INDEX_JOINED = 7
    INDEX_NOTES = 8
    INDEX_RANK = 9
    INDEX_CONTRIBUTION = 10
    INDEX_TEN_WEEK_AVERAGE = 11

    def __init__(self, index, grove_igns, mule_igns, name, score, discord_mention, introed, joined, notes, rank,
                 contribution, ten_week_average):
        try:
            self.index = int(index)
        except ValueError:
            self.index = -1
        self.grove_igns = str(grove_igns)
        self.mule_igns = str(mule_igns)
        self.name = str(name)
        try:
            self.score = int(score)
        except ValueError:
            self.score = 0
        self.discord_mention = str(discord_mention)
        self.introed = str(introed)
        self.joined = str(joined)
        self.notes = str(notes)
        self.rank = str(rank)
        try:
            self.contribution = int(contribution)
        except ValueError:
            self.contribution = 0
        try:
            self.ten_week_average = float(ten_week_average)
        except ValueError:
            self.ten_week_average = float(0)

    @property
    def discord_id(self):
        return int(self.discord_mention.strip('<@>'))

    @staticmethod
    def from_sheets_value(mp_value: list[str]):
        mp_value = mp_value[:MemberParticipation.LENGTH] + [''] * (MemberParticipation.LENGTH - len(mp_value))
        return MemberParticipation(mp_value[MemberParticipation.INDEX_INDEX],
                                   mp_value[MemberParticipation.INDEX_GROVE_IGNS],
                                   mp_value[MemberParticipation.INDEX_MULE_IGNS],
                                   mp_value[MemberParticipation.INDEX_NAME],
                                   mp_value[MemberParticipation.INDEX_SCORE],
                                   mp_value[MemberParticipation.INDEX_DISCORD_MENTION],
                                   mp_value[MemberParticipation.INDEX_INTROED],
                                   mp_value[MemberParticipation.INDEX_JOINED],
                                   mp_value[MemberParticipation.INDEX_NOTES], mp_value[MemberParticipation.INDEX_RANK],
                                   mp_value[MemberParticipation.INDEX_CONTRIBUTION],
                                   mp_value[MemberParticipation.INDEX_TEN_WEEK_AVERAGE])


def get_sorted_member_participation():
    mp_list = get_unsorted_member_participation()
    filtered = list(filter(lambda mp: mp.index != -1, mp_list))  # Remove invalid entries
    ordered_list = sorted(filtered, key=lambda mp: mp.index)  # First sort by index, i.e. in-game order
    sorted_list = sorted(ordered_list, key=lambda mp: mp.score, reverse=True)  # Then sort by score, descending

    return sorted_list


def get_unsorted_member_participation():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBER_PARTICIPATION).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    return list(map(lambda mp_value: MemberParticipation.from_sheets_value(mp_value), values))


def insert_weekly_participation_column(header: str):
    insert_column_body = {"requests": [{"insertDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_WEEKLY_PARTICIPATION,
                  "dimension": "COLUMNS",
                  "startIndex": 13,
                  "endIndex": 14},
        "inheritFromBefore": False
    }}]}

    try:
        sheets.get_service().spreadsheets().batchUpdate(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        body=insert_column_body).execute()

        body = {'values': [[header]]}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK_HEADER,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


def get_weekly_participation():
    def scores_from_sheets_value(sheets_value: list[int]):
        try:
            if len(sheets_value) == 0:
                return None
            else:
                return int(sheets_value[0])
        except ValueError:
            return None

    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_WEEK).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    return list(map(scores_from_sheets_value, values))


def update_weekly_participation(scores: list[int]):
    try:
        values = list(map(lambda score: [score], scores))
        body = {'values': values}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_WEEK,
                                                            valueInputOption="USER_ENTERED",
                                                            body=body).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


def get_custom_ign_mapping():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_CUSTOM_IGN_MAPPING).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    custom_ign_mapping = {}
    for value in values:
        custom_ign_mapping[value[1]] = value[0]
    return custom_ign_mapping


class Track:
    LENGTH = 9

    INDEX_DATE = 0
    INDEX_DISCORD_MENTION = 1
    INDEX_IGN = 2
    INDEX_GUILD = 3
    INDEX_MISSION = 4
    INDEX_CULVERT = 5
    INDEX_FLAG = 6
    INDEX_RAW_IGN = 7
    INDEX_MATCHED_PERCENT = 8

    def __init__(self, date: str, discord_mention: str, ign: str, guild: str, mission: int, culvert: int, flag: int,
                 raw_ign: str, matched_percent: int):
        self.date = date
        self.discord_mention = discord_mention
        self.ign = ign
        self.guild = guild
        self.mission = mission
        self.culvert = culvert
        self.flag = flag
        self.raw_ign = raw_ign
        self.matched_percent = matched_percent

    def __str__(self):
        return str(Track.to_sheets_value(self))

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [self.date, self.discord_mention, self.ign, self.guild, self.mission, self.culvert, self.flag,
                self.raw_ign, self.matched_percent]


def append_tracks(tracks: list[Track]):
    def track_to_sheets_values(sheets_track: Track):
        return sheets_track.to_sheets_value()

    body = {'values': list(map(track_to_sheets_values, tracks))}
    sheets.get_service().spreadsheets().values().append(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_TRACKING_DATA, valueInputOption="USER_ENTERED",
                                                        body=body).execute()


def append_errors(errors: list[str]):
    body = {'values': errors}
    sheets.get_service().spreadsheets().values().append(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_TRACKING_ERRORS, valueInputOption="USER_ENTERED",
                                                        body=body).execute()
