import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Callable, Coroutine

from birthday.sheets import Birthday as SheetsBirthday
from utils.constants import ONE_DAY_IN_SECONDS


class BirthdayService:

    class Event:

        class Type(Enum):
            start = "start"
            end = "end"

        def __init__(self, timestamp: int, event_type: Type, sheets_birthday: SheetsBirthday):
            self.timestamp = timestamp
            self.event_type = event_type
            self.sheets_birthday = sheets_birthday

        def __str__(self):
            return f'[{self.timestamp}, {self.event_type.name}, {self.sheets_birthday}]'

        def __repr__(self):
            return self.__str__()

    def __init__(self, on_start_absence: Callable[[SheetsBirthday], Coroutine],
                 on_end_absence: Callable[[SheetsBirthday], Coroutine]):
        self.on_start_birthday = on_start_absence
        self.on_end_birthday = on_end_absence
        self.absence_task: asyncio.Task = None

    def restart_service(self, sheets_birthdays: list[SheetsBirthday]):
        if self.absence_task:
            self.absence_task.cancel()

        self.absence_task = asyncio.create_task(self.service_loop(sheets_birthdays))

    async def service_loop(self, sheets_birthdays: list[SheetsBirthday]):
        # Create events list
        events: list[BirthdayService.Event] = []
        now = datetime.now()
        for sheets_birthday in sheets_birthdays:
            user_birthday = datetime.strptime(sheets_birthday.birthday_str, '%m-%d').replace(year=now.year,
                                                                                             tzinfo=timezone.utc)
            user_birthday = user_birthday + timedelta(hours=sheets_birthday.reset_offset)
            if user_birthday.timestamp() - now.timestamp() < -1 * ONE_DAY_IN_SECONDS:
                # Birthday is more than 24 hours ago
                user_birthday = user_birthday.replace(year=user_birthday.year + 1)

            events.append(BirthdayService.Event(int(user_birthday.timestamp()),
                                                BirthdayService.Event.Type.start,
                                                sheets_birthday))
            events.append(BirthdayService.Event(int(user_birthday.timestamp()) + ONE_DAY_IN_SECONDS,
                                                BirthdayService.Event.Type.end,
                                                sheets_birthday))

        events = sorted(events, key=lambda a: a.timestamp)

        while len(events) > 0:
            # Sleep until next event
            print(f'Next 5 events: {events[0:5]}')
            now = datetime.now()
            sleep_duration = events[0].timestamp - int(now.timestamp())
            if sleep_duration > 0:
                print(f'Birthday service sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            if events[0].event_type == BirthdayService.Event.Type.start:
                await self.on_start_birthday(events[0].sheets_birthday)
            elif events[0].event_type == BirthdayService.Event.Type.end:
                await self.on_end_birthday(events[0].sheets_birthday)

            # Push event to back, 1 year later
            sheets_birthday = events[0].sheets_birthday
            user_birthday = datetime.strptime(sheets_birthday.birthday_str, '%m-%d').replace(year=now.year + 1,
                                                                                             tzinfo=timezone.utc)
            user_birthday = user_birthday + timedelta(hours=sheets_birthday.reset_offset)

            events[0].timestamp = int(user_birthday.timestamp())
            if events[0].event_type == BirthdayService.Event.Type.end:
                events[0].timestamp += ONE_DAY_IN_SECONDS
            events = events[1:] + events[0:1]
