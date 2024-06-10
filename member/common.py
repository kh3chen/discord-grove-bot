import datetime

GUILD_CREATED_ON = datetime.date(2021, 12, 19)


def sunday():
    today = datetime.date.today()
    return today - datetime.timedelta(days=(today.weekday() + 1) % 7)


def guild_week():
    return (sunday() - GUILD_CREATED_ON).days // 7
