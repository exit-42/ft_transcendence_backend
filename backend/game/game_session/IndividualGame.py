from .IGame import *
from .PingPongMatch import *
import asyncio
import json
from websockets import WebSocketServerProtocol
from collections import namedtuple


class individual(IGame):

    async def start_match(self, player1_info, player2_info):
        match = PingPongMatch([player1_info, player2_info])
        asyncio.create_task(self.player_handler(player1_info.websocket, match, 1))
        asyncio.create_task(self.player_handler(player2_info.websocket, match, 2))
        result = await match.run()
        await self.send_log(result, player1_info, player2_info, 1)
        print(f"[Individual] Match finished. Winner: Player {result.winner}")

    async def matchmaker(self):
        while True:
            if len(self.waiting_queue) >= 2:
                p1_info = self.waiting_queue.pop(0)
                p2_info = self.waiting_queue.pop(0)
                self.game_start = True
                await asyncio.create_task(self.start_match(p1_info, p2_info))
                break
            await asyncio.sleep(0.1)
