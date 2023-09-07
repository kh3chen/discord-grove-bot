import asyncio
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine

from sheets_bossing import Party as SheetsParty


class BossTimeUpdater:
    SEVEN_DAYS_IN_SECONDS = 604800
    ONE_DAY_IN_SECONDS = 86400
    ONE_HOUR_IN_SECONDS = 3600

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

    def __init__(self, on_reminder: Callable[[SheetsParty], Coroutine], on_update: Callable[[SheetsParty], Coroutine]):
        self.on_reminder = on_reminder
        self.on_update = on_update
        self.updater_task: asyncio.Task = None

    def restart_updater(self, sheets_party: list[SheetsParty]):
        if self.updater_task:
            self.updater_task.cancel()

        self.updater_task = asyncio.create_task(self.updater_loop(sheets_party))

    async def updater_loop(self, sheets_party: list[SheetsParty]):
        # Create events list
        events: list[BossTimeUpdater.Event] = []
        now = int(datetime.timestamp(datetime.now()))
        for sheets_party in sheets_party:
            next_scheduled_time = sheets_party.next_scheduled_time()
            if next_scheduled_time:
                reminder_time = int(next_scheduled_time) - BossTimeUpdater.ONE_DAY_IN_SECONDS
                if reminder_time - now < 0:
                    # Reminder time is in the past
                    reminder_time += BossTimeUpdater.SEVEN_DAYS_IN_SECONDS
                index = 0
                for event in events:
                    if reminder_time < event.timestamp:
                        break
                    index += 1
                events[index:index] = [
                    BossTimeUpdater.Event(reminder_time, BossTimeUpdater.Event.Type.reminder, sheets_party)]

                update_time = int(next_scheduled_time) + BossTimeUpdater.ONE_HOUR_IN_SECONDS
                if update_time - now > BossTimeUpdater.SEVEN_DAYS_IN_SECONDS:
                    # Update time is more than 7 days away, so now is within an hour of the last scheduled run before its corresponding update
                    update_time -= BossTimeUpdater.SEVEN_DAYS_IN_SECONDS
                index = 0
                for event in events:
                    if update_time < event.timestamp:
                        break
                    index += 1
                events[index:index] = [
                    BossTimeUpdater.Event(update_time, BossTimeUpdater.Event.Type.update, sheets_party)]

        while True:
            # Sleep until next event
            print(f'Next 5 events: {events[0:5]}')
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = events[0].timestamp - now
            if sleep_duration > 0:
                print(f'Sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            if events[0].update_type == BossTimeUpdater.Event.Type.reminder:
                await self.on_reminder(events[0].sheets_party)
            elif events[0].update_type == BossTimeUpdater.Event.Type.update:
                await self.on_update(events[0].sheets_party)

            # Push event to back, 7 days later
            events[0].timestamp += BossTimeUpdater.SEVEN_DAYS_IN_SECONDS
            events = events[1:] + events[0:1]
