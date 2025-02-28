import IGame
import PingPongMatch
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
        self.send_log(result, player1_info, player2_info, 1)
        # print(f"[Individual] Match finished. Winner: Player {winner}")

    async def matchmaker(self):
        while True:
            if len(self.waiting_queue) >= 2:
                # 대기 중인 플레이어 2명을 꺼내서 경기를 시작합니다.
                p1_info = self.waiting_queue.pop(0)
                p2_info = self.waiting_queue.pop(0)
                # print("[Individual] Starting a match.")
                self.game_start = True
                await asyncio.create_task(self.start_match(p1_info, p2_info))
                break
            await asyncio.sleep(0.1)
