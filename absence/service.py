import asyncio
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine

from absence.sheets import Absence as SheetsAbsence


class AbsenceService:
    SEVEN_DAYS_IN_SECONDS = 604800
    ONE_DAY_IN_SECONDS = 86400
    ONE_HOUR_IN_SECONDS = 3600

    class Event:

        class Type(Enum):
            start = "start"
            end = "end"

        def __init__(self, timestamp: int, event_type: Type, sheets_absence: SheetsAbsence):
            self.timestamp = timestamp
            self.event_type = event_type
            self.sheets_absence = sheets_absence

        def __str__(self):
            return f'[{self.timestamp}, {self.event_type.name}, {self.sheets_absence}]'

        def __repr__(self):
            return self.__str__()

    def __init__(self, on_start_absence: Callable[[SheetsAbsence], Coroutine],
                 on_end_absence: Callable[[SheetsAbsence], Coroutine]):
        self.on_start_absence = on_start_absence
        self.on_end_absence = on_end_absence
        self.absence_task: asyncio.Task = None

    def restart_service(self, sheets_absences: list[SheetsAbsence]):
        if self.absence_task:
            self.absence_task.cancel()

        self.absence_task = asyncio.create_task(self.service_loop(sheets_absences))

    async def service_loop(self, sheets_absences: list[SheetsAbsence]):
        # sheets_absences must be ordered
        for sheets_absence in sheets_absences:
            # Sleep until next event
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = sheets_absence.timestamp - now
            if sleep_duration > 0:
                print(f'Sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            if sheets_absence.event_type == AbsenceService.Event.Type.start:
                await self.on_start_absence(sheets_absence)
            elif sheets_absence.event_type == AbsenceService.Event.Type.end:
                await self.on_end_absence(sheets_absence)
