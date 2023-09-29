import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:F'
RANGE_LEADERBOARD = 'Weekly Participation!A2:F'
RANGE_WEEK_HEADER = 'Weekly Participation!N1'


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

    new_members = list(map(lambda value: value[0],
                           (filter(lambda value: value[0] != '' and value[1] == '', values))))
    return new_members


def update_introed_new_members():
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])
    if not values:
        print('No data found.')
        return []

    for value in values:
        if value[0] != '' and value[1] == '':
            value[1] = 'Y'

    body = {'values': values}
    sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_MEMBERS, valueInputOption="RAW",
                                                        body=body).execute()


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


def update_member_rank(member_id: int, grove_role_name: str):
    service = sheets.get_service()
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                 range=RANGE_MEMBERS).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return []

    print(values)

    for value in values:
        if value[0] == f'<@{member_id}>':
            if len(value) == 1:
                value.append('')
                value.append(grove_role_name)
            elif len(value) == 2:
                value.append(grove_role_name)
            else:
                value[2] = grove_role_name

    body = {'values': values}
    sheets.get_service().spreadsheets().values().update(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_MEMBERS, valueInputOption="RAW",
                                                        body=body).execute()
