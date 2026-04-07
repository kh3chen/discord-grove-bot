import asyncio
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine

from bossing.sheets import Party as SheetsParty
from utils.constants import SEVEN_DAYS_IN_SECONDS

MAX_RETRIES = 5


def log(message):
    with open("bossing-service.log", "a") as f:
        f.write(f'{datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")} {message}\n')


class BossTimeService:
    CHECK_IN_OFFSET = -86400  # 24 hours before
    REMINDER_ONE_OFFSET = -21600  # 6 hours before
    REMINDER_TWO_OFFSET = -10800  # 3 hours before
    REMINDER_THREE_OFFSET = -3600  # 1 hour before
    REQUESTED_REMINDER_OFFSET = -900  # 15 minutes before
    UPDATE_OFFSET = 3600  # 1 hour after

    class Event:

        class Type(Enum):
            check_in = "check_in"
            check_in_reminder = "check_in_reminder"
            requested_reminder = "requested_reminder"
            run_start = "run_start"
            update = "update"

        def __init__(self, timestamp: int, update_type: Type, sheets_party: SheetsParty):
            self.timestamp = timestamp
            self.update_type = update_type
            self.sheets_party = sheets_party

        def __str__(self):
            return f'[{self.timestamp}, {self.update_type.name}, {self.sheets_party.name()}]'

        def __repr__(self):
            return self.__str__()

        def log_string(self):
            return f'<t:{self.timestamp}:F> - {self.sheets_party.name()} ({self.update_type.name})'

    def __init__(self,
                 on_check_in: Callable[[SheetsParty], Coroutine],
                 on_check_in_reminder: Callable[[SheetsParty], Coroutine],
                 on_requested_reminder: Callable[[SheetsParty], Coroutine],
                 on_run_start: Callable[[SheetsParty], Coroutine],
                 on_update: Callable[[SheetsParty], Coroutine]):
        self.on_check_in = on_check_in
        self.on_check_in_reminder = on_check_in_reminder
        self.on_requested_reminder = on_requested_reminder
        self.on_run_start = on_run_start
        self.on_update = on_update
        self.updater_task: asyncio.Task = None
        self.events: list[BossTimeService.Event] = []

    def restart_service(self, sheets_party: list[SheetsParty]):
        if self.updater_task:
            self.updater_task.cancel()

        self.updater_task = asyncio.create_task(self.service_loop(sheets_party))

    async def service_loop(self, sheets_parties: list[SheetsParty]):
        # Create events list
        self.events = []
        now = int(datetime.timestamp(datetime.now()))
        print('boss service loop start')
        for sheets_party in sheets_parties:
            await self.add_party_events(self.events, now, sheets_party)

        retry_count = 0
        while True:
            # Sleep until next event
            print(f'Next 5 bossing events: {self.events[0:5]}')
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = self.events[0].timestamp - now
            if sleep_duration > 0:
                print(f'Bossing service sleeping for {sleep_duration} seconds.')
                log(f'Bossing service sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            event = self.events.pop(0)
            log(event)
            try:
                if event.update_type == BossTimeService.Event.Type.check_in:
                    await self.on_check_in(event.sheets_party)
                elif event.update_type == BossTimeService.Event.Type.check_in_reminder:
                    await self.on_check_in_reminder(event.sheets_party)
                elif event.update_type == BossTimeService.Event.Type.requested_reminder:
                    await self.on_requested_reminder(event.sheets_party)
                elif event.update_type == BossTimeService.Event.Type.run_start:
                    await self.on_run_start(event.sheets_party)
                elif event.update_type == BossTimeService.Event.Type.update:
                    await self.on_update(event.sheets_party)
                    # Add party events for next scheduled run
                    await self.add_party_events(self.events, int(datetime.timestamp(datetime.now())),
                                                event.sheets_party)
            except Exception as e:
                print(f'{type(e).__name__}: {e}')
                log(f'{type(e).__name__}: {e}')
                log(self.events)
                if retry_count < MAX_RETRIES:
                    self.events.insert(0, event)
                    retry_count += 1
                    error_retry_sleep_duration = retry_count * retry_count
                    log(f'Error retry #{retry_count} - Sleeping for {error_retry_sleep_duration}s')
                    await asyncio.sleep(retry_count * retry_count)
                else:
                    retry_count = 0

    async def add_party_events(self, events, now, sheets_party):
        next_scheduled_time = sheets_party.next_scheduled_time()
        if next_scheduled_time:
            # Check-in
            check_in_time = next_scheduled_time + BossTimeService.CHECK_IN_OFFSET
            if check_in_time - now > 0:
                check_in_event = BossTimeService.Event(check_in_time,
                                                       BossTimeService.Event.Type.check_in,
                                                       sheets_party)
                self.__insert_event(events, check_in_event)
                log(f'Add event: {check_in_event}')

            # Reminder 1
            reminder_one_time = next_scheduled_time + BossTimeService.REMINDER_ONE_OFFSET
            if reminder_one_time - now > 0:
                reminder_one_event = BossTimeService.Event(reminder_one_time,
                                                           BossTimeService.Event.Type.check_in_reminder,
                                                           sheets_party)
                self.__insert_event(events, reminder_one_event)
                log(f'Add event: {reminder_one_event}')

            # Reminder 2
            reminder_two_time = next_scheduled_time + BossTimeService.REMINDER_TWO_OFFSET
            if reminder_two_time - now > 0:
                reminder_two_event = BossTimeService.Event(reminder_two_time,
                                                           BossTimeService.Event.Type.check_in_reminder,
                                                           sheets_party)
                self.__insert_event(events, reminder_two_event)
                log(f'Add event: {reminder_two_event}')

            # Reminder 3
            reminder_three_time = next_scheduled_time + BossTimeService.REMINDER_THREE_OFFSET
            if reminder_three_time - now > 0:
                reminder_three_event = BossTimeService.Event(reminder_three_time,
                                                             BossTimeService.Event.Type.check_in_reminder,
                                                             sheets_party)
                self.__insert_event(events, reminder_three_event)
                log(f'Add event: {reminder_three_event}')

            # Requested reminder
            requested_reminder_time = next_scheduled_time + BossTimeService.REQUESTED_REMINDER_OFFSET
            if requested_reminder_time - now > 0:
                requested_reminder_event = BossTimeService.Event(requested_reminder_time,
                                                                 BossTimeService.Event.Type.requested_reminder,
                                                                 sheets_party)
                self.__insert_event(events, requested_reminder_event)
                log(f'Add event: {requested_reminder_event}')

            # Update
            update_time = next_scheduled_time + BossTimeService.UPDATE_OFFSET
            if update_time - now > SEVEN_DAYS_IN_SECONDS:
                # Update time is more than 7 days away, so now is within an hour of the last scheduled run before its corresponding update
                update_time -= SEVEN_DAYS_IN_SECONDS
            update_event = BossTimeService.Event(update_time,
                                                 BossTimeService.Event.Type.update,
                                                 sheets_party)
            self.__insert_event(events, update_event)
            log(f'Add event: {update_event}')

    def get_event_logs(self, event_count: int):
        return [event.log_string() for event in self.events[0:event_count]]

    @staticmethod
    def __insert_event(events: list[Event], new_event: Event):
        index = 0
        for event in events:
            if new_event.timestamp < event.timestamp:
                break
            index += 1
        events[index:index] = [new_event]
