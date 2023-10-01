import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:F'
RANGE_LEADERBOARD = 'Weekly Participation!A2:F'
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


def get_leaderboard():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_LEADERBOARD).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    filtered = list(filter(lambda l: len(l) == 6 and int(l[4]) > 0, values))
    ordered_list = sorted(filtered, key=lambda l: float(l[0]))
    sorted_list = sorted(ordered_list, key=lambda l: float(l[4]), reverse=True)

    output = []
    current_score = None
    line = ''
    for member in sorted_list:
        score = member[4]
        discord_id = member[5]

        if score != current_score:
            if current_score is not None:
                output.append(line)
            line = f'{score} '
        line += f'{discord_id} '
        current_score = score

    if current_score is not None:
        output.append(line)

    return output
