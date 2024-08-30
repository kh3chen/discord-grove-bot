import datetime

GUILD_CREATED_ON = datetime.date(2021, 12, 19)

THURSDAY_WEEKDAY = 3


def thursday():
    today = datetime.date.today()
    return today - datetime.timedelta(days=(today.weekday() - THURSDAY_WEEKDAY) % 7)


def guild_week():
    return (thursday() - GUILD_CREATED_ON).days // 7
