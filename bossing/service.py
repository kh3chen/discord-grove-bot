import asyncio
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine

from bossing.sheets import Party as SheetsParty


class BossTimeService:
    SEVEN_DAYS_IN_SECONDS = 604800
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
            return f'[{self.timestamp}, {self.update_type.name}, {self.sheets_party}]'

        def __repr__(self):
            return self.__str__()

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

    def restart_service(self, sheets_party: list[SheetsParty]):
        if self.updater_task:
            self.updater_task.cancel()

        self.updater_task = asyncio.create_task(self.service_loop(sheets_party))

    async def service_loop(self, sheets_parties: list[SheetsParty]):
        # Create events list
        events: list[BossTimeService.Event] = []
        now = int(datetime.timestamp(datetime.now()))
        for sheets_party in sheets_parties:
            next_scheduled_time = sheets_party.next_scheduled_time()
            if next_scheduled_time:
                # Check-in
                check_in_time = int(next_scheduled_time) + BossTimeService.CHECK_IN_OFFSET
                if check_in_time - now < 0:
                    # Check-in time is in the past
                    check_in_time += BossTimeService.SEVEN_DAYS_IN_SECONDS
                self.__insert_event(events,
                                    BossTimeService.Event(check_in_time,
                                                          BossTimeService.Event.Type.check_in,
                                                          sheets_party))

                # Reminder 1
                reminder_one_time = int(next_scheduled_time) + BossTimeService.REMINDER_ONE_OFFSET
                if reminder_one_time - now < 0:
                    # Reminder time is in the past
                    reminder_one_time += BossTimeService.SEVEN_DAYS_IN_SECONDS
                self.__insert_event(events,
                                    BossTimeService.Event(reminder_one_time,
                                                          BossTimeService.Event.Type.check_in_reminder,
                                                          sheets_party))

                # Reminder 2
                reminder_two_time = int(next_scheduled_time) + BossTimeService.REMINDER_TWO_OFFSET
                if reminder_two_time - now < 0:
                    # Reminder time is in the past
                    reminder_two_time += BossTimeService.SEVEN_DAYS_IN_SECONDS
                self.__insert_event(events,
                                    BossTimeService.Event(reminder_two_time,
                                                          BossTimeService.Event.Type.check_in_reminder,
                                                          sheets_party))

                # Reminder 3
                reminder_three_time = int(next_scheduled_time) + BossTimeService.REMINDER_THREE_OFFSET
                if reminder_three_time - now < 0:
                    # Reminder time is in the past
                    reminder_three_time += BossTimeService.SEVEN_DAYS_IN_SECONDS
                self.__insert_event(events,
                                    BossTimeService.Event(reminder_three_time,
                                                          BossTimeService.Event.Type.check_in_reminder,
                                                          sheets_party))

                # Requested reminder
                requested_reminder_time = int(next_scheduled_time) + BossTimeService.REQUESTED_REMINDER_OFFSET
                if requested_reminder_time - now < 0:
                    # Reminder time is in the past
                    requested_reminder_time += BossTimeService.SEVEN_DAYS_IN_SECONDS
                self.__insert_event(events,
                                    BossTimeService.Event(requested_reminder_time,
                                                          BossTimeService.Event.Type.requested_reminder,
                                                          sheets_party))

                # # Boss run
                # boss_run_time = int(next_scheduled_time)
                # if boss_run_time - now < 0:
                #     # Boss run time is in the past
                #     boss_run_time += BossTimeService.SEVEN_DAYS_IN_SECONDS
                # self.__insert_event(events,
                #                     BossTimeService.Event(boss_run_time,
                #                                           BossTimeService.Event.Type.run_start,
                #                                           sheets_party))

                # Update
                update_time = int(next_scheduled_time) + BossTimeService.UPDATE_OFFSET
                if update_time - now > BossTimeService.SEVEN_DAYS_IN_SECONDS:
                    # Update time is more than 7 days away, so now is within an hour of the last scheduled run before its corresponding update
                    update_time -= BossTimeService.SEVEN_DAYS_IN_SECONDS
                self.__insert_event(events,
                                    BossTimeService.Event(update_time,
                                                          BossTimeService.Event.Type.update,
                                                          sheets_party))

        while True:
            # Sleep until next event
            print(f'Next 5 events: {events[0:5]}')
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = events[0].timestamp - now
            if sleep_duration > 0:
                print(f'Bossing service sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            if events[0].update_type == BossTimeService.Event.Type.check_in:
                await self.on_check_in(events[0].sheets_party)
            elif events[0].update_type == BossTimeService.Event.Type.check_in_reminder:
                await self.on_check_in_reminder(events[0].sheets_party)
            elif events[0].update_type == BossTimeService.Event.Type.requested_reminder:
                await self.on_requested_reminder(events[0].sheets_party)
            elif events[0].update_type == BossTimeService.Event.Type.run_start:
                await self.on_run_start(events[0].sheets_party)
            elif events[0].update_type == BossTimeService.Event.Type.update:
                await self.on_update(events[0].sheets_party)

            # Push event to back, 7 days later
            events[0].timestamp += BossTimeService.SEVEN_DAYS_IN_SECONDS
            events = events[1:] + events[0:1]

    @staticmethod
    def __insert_event(events: list[Event], new_event: Event):
        index = 0
        for event in events:
            if new_event.timestamp < event.timestamp:
                break
            index += 1
        events[index:index] = [new_event]
