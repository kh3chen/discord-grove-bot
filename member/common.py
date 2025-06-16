import datetime

GUILD_CREATED_ON = datetime.date(2021, 12, 19)

THURSDAY_WEEKDAY = 3


def thursday(date=datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0,
                                                    tzinfo=datetime.timezone.utc)):
    return date - datetime.timedelta(days=(date.weekday() - THURSDAY_WEEKDAY) % 7)


def guild_week():
    return (thursday() - GUILD_CREATED_ON).days // 7
