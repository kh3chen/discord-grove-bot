import asyncio
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine

from away.sheets import Away as SheetsAway


class AwayService:
    SEVEN_DAYS_IN_SECONDS = 604800
    ONE_DAY_IN_SECONDS = 86400
    ONE_HOUR_IN_SECONDS = 3600

    class Event:

        class Type(Enum):
            set = "set"
            clear = "clear"

        def __init__(self, timestamp: int, event_type: Type, sheets_away: SheetsAway):
            self.timestamp = timestamp
            self.event_type = event_type
            self.sheets_away = sheets_away

        def __str__(self):
            return f'[{self.timestamp}, {self.event_type.name}, {self.sheets_away}]'

        def __repr__(self):
            return self.__str__()

    def __init__(self, on_set_away: Callable[[SheetsAway], Coroutine],
                 on_clear_away: Callable[[SheetsAway], Coroutine]):
        self.on_set_away = on_set_away
        self.on_clear_away = on_clear_away
        self.away_task: asyncio.Task = None

    def restart_service(self, sheets_away: list[SheetsAway]):
        if self.away_task:
            self.away_task.cancel()

        self.away_task = asyncio.create_task(self.service_loop(sheets_away))

    async def service_loop(self, sheets_aways: list[SheetsAway]):
        # sheets_aways must be ordered
        for sheets_away in sheets_aways:
            # Sleep until next event
            now = int(datetime.timestamp(datetime.now()))
            sleep_duration = sheets_away.timestamp - now
            if sleep_duration > 0:
                print(f'Sleeping for {sleep_duration} seconds.')
                await asyncio.sleep(sleep_duration)

            # Fire event
            if sheets_away.event_type == AwayService.Event.Type.set:
                await self.on_set_away(sheets_away)
            elif sheets_away.event_type == AwayService.Event.Type.clear:
                await self.on_clear_away(sheets_away)
