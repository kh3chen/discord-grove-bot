import config
from utils import sheets

SHEET_MEMBER_TRACKING = config.MEMBER_TRACKING_SPREADSHEET_ID  # The ID of the member tracking sheet
RANGE_CULVERT_WEEKS_DATES = 'Culvert!E2:I2'
RANGE_CULVERT_WEEKS_SCORES = 'Culvert!D3:I'
RANGE_CULVERT_MAX_SCORES = 'Culvert!A2:B'


class CulvertWeeks:
    LENGTH = 6

    INDEX_IGN = 0

    def __init__(self, ign: str, scores: dict[str, int]):
        self.ign = ign
        self.scores = scores

    @staticmethod
    def from_sheets_value(dates: list[str], culvert_value: list[str]):
        culvert_value = culvert_value + [''] * (1 + len(dates) - len(culvert_value))
        scores = {}
        for x in range(len(dates)):
            try:
                scores[dates[x]] = int(culvert_value[x + 1])
            except ValueError:
                scores[dates[x]] = None
        return CulvertWeeks(culvert_value[CulvertWeeks.INDEX_IGN],
                            scores)


def get_culvert_weeks_scores():
    service = sheets.get_service()

    dates_result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                       range=RANGE_CULVERT_WEEKS_DATES).execute()
    dates = dates_result.get('values', [])[0]

    scores_result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                        range=RANGE_CULVERT_WEEKS_SCORES).execute()
    scores_values = scores_result.get('values', [])

    if not scores_values:
        print('No data found.')
        return

    return list(map(lambda culvert_value: CulvertWeeks.from_sheets_value(dates, culvert_value), scores_values))


class CulvertMax:
    LENGTH = 2

    INDEX_IGN = 0
    INDEX_SCORE = 1

    def __init__(self, ign: str, score: int):
        self.ign = ign
        self.score = score

    @staticmethod
    def from_sheets_value(culvert_max_value: list[str]):
        return CulvertMax(culvert_max_value[CulvertMax.INDEX_IGN],
                          int(culvert_max_value[CulvertMax.INDEX_SCORE]))


def get_culvert_max_scores():
    service = sheets.get_service()

    max_scores_result = service.spreadsheets().values().get(spreadsheetId=SHEET_MEMBER_TRACKING,
                                                            range=RANGE_CULVERT_MAX_SCORES).execute()
    culvert_max_values = max_scores_result.get('values', [])

    if not culvert_max_values:
        print('No data found.')
        return

    return list(map(lambda culvert_max_value: CulvertMax.from_sheets_value(culvert_max_value), culvert_max_values))
