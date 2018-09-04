from heapq import heappop, heappush
from functools import total_ordering
from typing import Any
import asyncio

class SchedulerQueue:
    def __init__(self):
        self.queue = []
        self.qsize = 0
        self.lastBlock = 0
        self.lock = asyncio.Lock()
        self.modify = asyncio.Lock()

    # We take a guid here, not for any functionality, but to prevent
    # the heap from trying to compare the functions if blocknumber is the same
    # between two scheduled events.
    async def schedule(self, task):
        await self.modify.acquire()
        heappush(self.queue, task)
        self.qsize += 1
        self.modify.release()

    async def pop(self):
        value = None
        await self.modify.acquire()
        if self.qsize > 0:
            self.qsize -= 1
            value = heappop(self.queue)

        self.modify.release()
        return value

    async def execute_scheduled(self, blocknumber):
        # Have to lock because block events hit multiple times
        await self.lock.acquire()
        block = int(blocknumber)
        if block > self.lastBlock:
            self.lastBlock = block
            event = await self.pop()
            while event is not None:
                expiration = event.priority
                if expiration < block:
                    await event.execute()
                    event = await self.pop()
                else:
                    # Throw it back on the front
                    await self.schedule(event)
                    break
        self.lock.release()

@total_ordering
class SchedulerTask:
    def __init__(self, priority, function, args):
        self.priority = priority
        self.function = function
        self.args = args

    def __eq__(self, other):
        return self.priority == other.priority

    def __lt__(self, other):
        return self.priority < other.priority

    async def execute(self):
        await self.function(**self.args)
