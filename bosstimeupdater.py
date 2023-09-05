import asyncio
import bisect
import time
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine

from sheets_bossing import Party as SheetsParty
from sheets_bossing import SheetsBossing


class BossTimeUpdater:
    SEVEN_DAYS_IN_SECONDS = 604800
    ONE_DAY_IN_SECONDS = 86400

    class Event:

        class Type(Enum):
            reminder = "reminder"
            update = "update"

        def __init__(self, timestamp: int, update_type: Type, sheets_party: SheetsParty):
            self.timestamp = timestamp
            self.update_type = update_type
            self.sheets_party = sheets_party

        def __str__(self):
            return f'[{self.timestamp}, {self.update_type.name}, {self.sheets_party}]'

        def __repr__(self):
            return self.__str__()

    def __init__(self, bot, sheets_bossing: SheetsBossing, on_update: Callable[[SheetsParty], Coroutine]):
        self.bot = bot
        self.sheets_bossing = sheets_bossing
        self.on_update = on_update
        self.updater_task: asyncio.Task = None

        self.restart_updater()

    def restart_updater(self):
        if self.updater_task:
            self.updater_task.cancel()
        else:
            self.updater_task = asyncio.create_task(self.updater_loop())

    async def updater_loop(self):
        events: list[BossTimeUpdater.Event] = []
        for sheets_party in self.sheets_bossing.parties:
            next_scheduled_time = sheets_party.next_scheduled_time()
            if next_scheduled_time:
                reminder_time = int(next_scheduled_time) - BossTimeUpdater.ONE_DAY_IN_SECONDS
                bisect.insort(events,
                              BossTimeUpdater.Event(reminder_time, BossTimeUpdater.Event.Type.reminder, sheets_party),
                              key=lambda e: e.timestamp)
                update_time = int(next_scheduled_time)
                bisect.insort(events,
                              BossTimeUpdater.Event(update_time, BossTimeUpdater.Event.Type.update, sheets_party),
                              key=lambda event: event.timestamp)

        while True:
            print(events)
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = events[0].timestamp - now
            if sleep_duration < 0:
                events[0].timestamp += BossTimeUpdater.SEVEN_DAYS_IN_SECONDS
                events = events[1:] + events[0:1]
                continue

            print(f'Sleeping for {sleep_duration} seconds.')
            await asyncio.sleep(sleep_duration)
            print(f'Woke up!')
            test_channel = self.bot.get_channel(1148466293637402754)
            if events[0].update_type == BossTimeUpdater.Event.Type.reminder:
                await test_channel.send(
                    f'Reminder for <@&{events[0].sheets_party.role_id}>, run is in 24 hours at {events[0].sheets_party.next_scheduled_time()}')
            elif events[0].update_type == BossTimeUpdater.Event.Type.update:
                await self.on_update(events[0].sheets_party)

            events[0].timestamp += BossTimeUpdater.SEVEN_DAYS_IN_SECONDS
            events = events[1:] + events[0:1]
