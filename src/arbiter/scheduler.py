from heapq import heappop, heappush
import asyncio

class SchedulerQueue:
    def __init__(self):
        self.queue = []
        self.qsize = 0
        self.lastBlock = 0
        self.lock = asyncio.Lock()
        self.modify = asyncio.Lock()

    async def schedule(self, blocknumber, function, args):
        await self.modify.acquire()
        heappush(self.queue, (blocknumber, (function, args)))
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
                expiration = event[0]
                function = event[1][0]
                args = event[1][1]
                if int(expiration) < block:
                    await function(**args)
                    event = await self.pop()
                else:
                    # Throw it back on the front
                    await self.schedule(expiration, function, args)
                    break
        self.lock.release()