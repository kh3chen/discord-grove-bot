import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:F'
RANGE_WEEKLY_PARTICIPATION = 'Weekly Participation!A2:L'
RANGE_WEEK_HEADER = 'Weekly Participation!N1'


class Member:
    LENGTH = 3

    INDEX_DISCORD_MENTION = 0
    INDEX_INTROED = 1
    INDEX_RANK = 2

    def __init__(self, discord_mention: str, introed: str, rank: str):
        self.discord_mention = discord_mention
        self.introed = introed
        self.rank = rank

    @staticmethod
    def from_sheets_value(members_value: list[str]):
        members_value = members_value[:Member.LENGTH] + [''] * (Member.LENGTH - len(members_value))
        return Member(members_value[Member.INDEX_DISCORD_MENTION],
                      members_value[Member.INDEX_INTROED],
                      members_value[Member.INDEX_RANK])

    def __str__(self):
        return str(self.to_sheets_value())

    def __repr__(self):
        return self.__str__()

    def to_sheets_value(self):
        return [self.discord_mention, self.introed, self.rank]


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
    new_members = filter(lambda member: member.discord_mention != '' and member.introed == '', members)
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
        if member.discord_mention != '' and member.introed == '':
            member.introed = 'Y'

    body = {'values': list(map(lambda member: member.to_sheets_value(), members))}
    sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_MEMBERS, valueInputOption="RAW",
                                                        body=body).execute()


def update_member_rank(member_id: int, grove_role_name: str):
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return []

    members = list(map(lambda value: Member.from_sheets_value(value), values))
    try:
        member = next(member for member in members if
                      member.discord_mention == f'<@{member_id}>')
        member.rank = grove_role_name

        body = {'values': list(map(lambda member: member.to_sheets_value(), members))}
        sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_MEMBERS, valueInputOption="RAW",
                                                            body=body).execute()
    except StopIteration:
        return


class WeeklyParticipation:
    LENGTH = 12

    INDEX_INDEX = 0
    INDEX_GROVE_IGNS = 1
    INDEX_NAME = 2
    INDEX_MULE_IGNS = 3
    INDEX_SCORE = 4
    INDEX_DISCORD_ID = 5
    INDEX_INTROED = 6
    INDEX_JOINED = 7
    INDEX_NOTES = 8
    INDEX_RANK = 9
    INDEX_CONTRIBUTION = 10
    INDEX_TEN_WEEK_AVERAGE = 11

    def __init__(self, index, grove_igns, name, mule_igns, score, discord_id, introed, joined, notes, rank,
                 contribution, ten_week_average):
        try:
            self.index = int(index)
        except ValueError:
            self.index = -1
        self.grove_igns = str(grove_igns)
        self.name = str(name)
        self.mule_igns = str(mule_igns)
        try:
            self.score = int(score)
        except ValueError:
            self.score = 0
        self.discord_id = str(discord_id)
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

    @staticmethod
    def from_sheets_value(wp_value: list[str]):
        wp_value = wp_value[:WeeklyParticipation.LENGTH] + [''] * (WeeklyParticipation.LENGTH - len(wp_value))
        return WeeklyParticipation(wp_value[WeeklyParticipation.INDEX_INDEX],
                                   wp_value[WeeklyParticipation.INDEX_GROVE_IGNS],
                                   wp_value[WeeklyParticipation.INDEX_NAME],
                                   wp_value[WeeklyParticipation.INDEX_MULE_IGNS],
                                   wp_value[WeeklyParticipation.INDEX_SCORE],
                                   wp_value[WeeklyParticipation.INDEX_DISCORD_ID],
                                   wp_value[WeeklyParticipation.INDEX_INTROED],
                                   wp_value[WeeklyParticipation.INDEX_JOINED],
                                   wp_value[WeeklyParticipation.INDEX_NOTES], wp_value[WeeklyParticipation.INDEX_RANK],
                                   wp_value[WeeklyParticipation.INDEX_CONTRIBUTION],
                                   wp_value[WeeklyParticipation.INDEX_TEN_WEEK_AVERAGE])


def get_weekly_participation():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_WEEKLY_PARTICIPATION).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    wp_list = list(map(lambda wp_value: WeeklyParticipation.from_sheets_value(wp_value), values))
    return list(filter(lambda wp: wp.index != -1, wp_list))
