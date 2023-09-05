import asyncio
import bisect
from enum import Enum

from sheets_bossing import SheetsBossing


class BossTimeUpdater:
    SEVEN_DAYS_IN_SECONDS = 604800
    ONE_HOUR_IN_SECONDS = 3600

    class Update:

        class Type(Enum):
            Reminder = "Reminder"
            Next = "Next"

        def __init__(self, timestamp, update_type, sheets_party):
            self.timestamp = timestamp
            self.update_type = update_type
            self.sheets_party = sheets_party

    def __init__(self, bot, sheets_bossing: SheetsBossing):
        self.bot = bot
        self.sheets_bossing = sheets_bossing
        self.updater_task: asyncio.Task = None

        self.restart_updater()

    def restart_updater(self):
        if self.updater_task:
            self.updater_task.cancel()
        else:
            self.updater_task = asyncio.create_task(self.updater_loop())

    async def updater_loop(self):
        reminders = []
        for sheets_party in self.sheets_bossing.parties:
            next_scheduled_time = int(sheets_party.next_scheduled_time())
            print(f'{next_scheduled_time}: {sheets_party}')
            if next_scheduled_time:
                reminder_time = next_scheduled_time - BossTimeUpdater.SEVEN_DAYS_IN_SECONDS
                bisect.insort(reminders,
                              BossTimeUpdater.Update(reminder_time, BossTimeUpdater.Update.Type.Reminder, sheets_party),
                              key=lambda update: update.timestamp)

        print(reminders)
