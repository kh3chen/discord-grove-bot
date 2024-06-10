import datetime
from enum import Enum

from googleapiclient.errors import HttpError

import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:G'
RANGE_WEEKLY_PARTICIPATION = 'Weekly Participation!A2:ZZZ'
RANGE_WEEK_HEADER = 'Weekly Participation!N1'
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


def get_new_members():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return []

    members = list(map(lambda value: Member.from_sheets_value(value), values))
    new_members = filter(
        lambda
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

    # Weekly Participation
    weekly_participation = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                               range=RANGE_WEEKLY_PARTICIPATION).execute()
    wp_values = weekly_participation.get('values', [])

    if not wp_values:
        print('No data found.')
        return

    member_wp_value = None
    wp_delete_index = 1  # Offset by 1 due to header rows
    for wp_value in wp_values:
        if wp_value[WeeklyParticipation.INDEX_DISCORD_MENTION] == f'<@{member_id}>':
            # Found the entry
            member_wp_value = wp_value
            break
        wp_delete_index += 1

    if wp_delete_index >= len(wp_values) or member_wp_value is None:
        # Cannot find weekly participation value
        return

    # Append value to Past Members sheet
    past_member_value = [datetime.date.today().strftime('%Y-%m-%d'), reason] + member_wp_value[1:]
    body = {'values': [past_member_value]}
    service.spreadsheets().values().append(spreadsheetId=config.MEMBER_TRACKING_SPREADSHEET_ID,
                                           range=RANGE_PAST_MEMBERS,
                                           valueInputOption="USER_ENTERED",
                                           body=body).execute()

    # Delete Weekly Participation row
    wp_delete_body = {"requests": [{"deleteDimension": {
        "range": {"sheetId": config.MEMBER_TRACKING_SHEET_ID_WEEKLY_PARTICIPATION, "dimension": "ROWS",
                  "startIndex": wp_delete_index,
                  "endIndex": wp_delete_index + 1}}}]}
    try:
        service.spreadsheets().batchUpdate(spreadsheetId=config.MEMBER_TRACKING_SPREADSHEET_ID,
                                           body=wp_delete_body).execute()
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
        return WeeklyParticipation.from_sheets_value(member_wp_value)

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


class WeeklyParticipation:
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
    def from_sheets_value(wp_value: list[str]):
        wp_value = wp_value[:WeeklyParticipation.LENGTH] + [''] * (WeeklyParticipation.LENGTH - len(wp_value))
        return WeeklyParticipation(wp_value[WeeklyParticipation.INDEX_INDEX],
                                   wp_value[WeeklyParticipation.INDEX_GROVE_IGNS],
                                   wp_value[WeeklyParticipation.INDEX_MULE_IGNS],
                                   wp_value[WeeklyParticipation.INDEX_NAME],
                                   wp_value[WeeklyParticipation.INDEX_SCORE],
                                   wp_value[WeeklyParticipation.INDEX_DISCORD_MENTION],
                                   wp_value[WeeklyParticipation.INDEX_INTROED],
                                   wp_value[WeeklyParticipation.INDEX_JOINED],
                                   wp_value[WeeklyParticipation.INDEX_NOTES], wp_value[WeeklyParticipation.INDEX_RANK],
                                   wp_value[WeeklyParticipation.INDEX_CONTRIBUTION],
                                   wp_value[WeeklyParticipation.INDEX_TEN_WEEK_AVERAGE])


def get_sorted_weekly_participation():
    wp_list = get_unsorted_weekly_participation()
    filtered = list(filter(lambda wp: wp.index != -1, wp_list))  # Remove invalid entries
    ordered_list = sorted(filtered, key=lambda wp: wp.index)  # First sort by index, i.e. in-game order
    sorted_list = sorted(ordered_list, key=lambda wp: wp.score, reverse=True)  # Then sort by score, descending

    return sorted_list


def get_unsorted_weekly_participation():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_WEEKLY_PARTICIPATION).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    return list(map(lambda wp_value: WeeklyParticipation.from_sheets_value(wp_value), values))


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
        custom_ign_mapping[value[0]] = value[1]
    return custom_ign_mapping


class Track:
    LENGTH = 6

    INDEX_DATE = 0
    INDEX_DISCORD_MENTION = 1
    INDEX_IGN = 2
    INDEX_MISSION = 3
    INDEX_CULVERT = 4
    INDEX_FLAG = 5

    def __init__(self, date: str, discord_mention: str, ign: str, mission: str, culvert: int, flag: int):
        self.date = date
        self.discord_mention = discord_mention
        self.ign = ign
        self.mission = mission
        self.culvert = culvert
        self.flag = flag

    def __str__(self):
        return str(Track.to_sheets_value(self))

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [self.date, self.discord_mention, self.ign, self.mission, self.culvert, self.flag]


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
