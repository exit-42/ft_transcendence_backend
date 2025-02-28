from .IGame import *
from .PingPongMatch import *
import asyncio
import json
from websockets import WebSocketServerProtocol


class tournament(IGame):
    async def start_match(self, player1_info, player2_info):
        match = PingPongMatch(player1_info, player2_info)
        asyncio.create_task(self.player_handler(player1_info.websocket, match, 1))
        asyncio.create_task(self.player_handler(player2_info.websocket, match, 2))
        winner = await match.run()
        return player1_info if winner == 1 else player2_info

    async def matchmaker(self):
        while True:
            if len(self.waiting_queue) >= 4:
                # 4명의 플레이어를 꺼냅니다.
                p1_info = self.waiting_queue.pop(0)
                p2_info = self.waiting_queue.pop(0)
                p3_info = self.waiting_queue.pop(0)
                p4_info = self.waiting_queue.pop(0)

                self.game_start = True
                # print("[Tournament] Starting round 1 matches.")
                # 라운드1: 두 경기를 동시에 진행 (1:1)
                task1 = asyncio.create_task(
                    self.start_match(p1_info, p2_info, "tournament_round1_match1")
                )
                task2 = asyncio.create_task(
                    self.start_match(p3_info, p4_info, "tournament_round1_match2")
                )
                result1 = await task1
                result2 = await task2
                await self.send_log(result1, p1_info, p2_info, 1)
                await self.send_log(result2, p3_info, p4_info, 1)

                winner1 = result1.winner
                winner2 = result2.winner
                # 결승 진출 알림 전송
                final_msg = json.dumps(
                    {
                        "type": "final_info",
                        "player1": winner1.username,
                        "player2": winner2.username,
                    }
                )
                try:
                    for p in [p1_info, p2_info, p3_info, p4_info]:
                        self.send(final_msg)
                except:
                    pass

                watch_list = []
                for p in [p1_info, p2_info, p3_info, p4_info]:
                    if p is not winner1 and p is not winner2:
                        watch_list.append(p)

                # print("[Tournament] Starting final match.")
                final_match = PingPongMatch(
                    winner1, winner2, watch_list
                )
                asyncio.create_task(self.player_handler(winner1.websocket, final_match, 1))
                asyncio.create_task(self.player_handler(winner2.websocket, final_match, 2))
                final_result = await final_match.run()
                await self.send_log(final_result, winner1, winner2, 1)
                # print(f"[Tournament] Tournament finished. Final Winner: Player {final_winner}")
                for p in [p1_info, p2_info, p3_info, p4_info]:
                    try:
                        await p.close()
                    except:
                        pass
                await self.system.close()
            await asyncio.sleep(0.1)
