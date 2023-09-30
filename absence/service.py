import asyncio
from datetime import datetime
from typing import Callable, Coroutine

from absence.sheets import Absence as SheetsAbsence


class AbsenceService:

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
        print(sheets_absences)
        sorted_sheets_absences = sorted(sheets_absences, key=lambda a: a.timestamp)
        print(sorted_sheets_absences)
        for sheets_absence in sorted_sheets_absences:
            # Sleep until next event
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = int(sheets_absence.timestamp) - now
            if sleep_duration > 0:
                print(f'Absence service sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            if sheets_absence.event_type == SheetsAbsence.Type.start:
                await self.on_start_absence(sheets_absence)
            elif sheets_absence.event_type == SheetsAbsence.Type.end:
                await self.on_end_absence(sheets_absence)
