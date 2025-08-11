import datetime

GUILD_CREATED_ON = datetime.datetime.utcfromtimestamp(1639872000)  # 2021-12-19 0:00 UTC

THURSDAY_WEEKDAY = 3


def thursday(date=None):
    if date is None:
        date = datetime.datetime.utcnow()
    return date.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(
        days=(date.weekday() - THURSDAY_WEEKDAY) % 7)


def guild_week():
    return (thursday() - GUILD_CREATED_ON).days // 7
