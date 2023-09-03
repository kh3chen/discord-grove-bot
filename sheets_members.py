import itertools

import config
import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_MEMBERS = 'Member List!D3:E'
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

    new_members = list(filter(lambda l: len(l) == 1, values))
    return list(itertools.chain(*new_members))  # flatten


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
        index = member[0]
        score = member[4]
        discord_id = member[5]
        # print(f'{index}, {score}, {discord_id}')

        if score != current_score:
            if current_score is not None:
                output.append(line)
            line = f'{score} '
        line += f'{discord_id} '
        current_score = score

    if current_score is not None:
        output.append(line)

    # print(output)
    return output
