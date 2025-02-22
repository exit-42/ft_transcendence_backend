import IGame
import PingPongMatch
import asyncio
import json
import urllib.parse

class tournament(IGame):
    async def register(self, websocket, path):
        parsed = urllib.parse.urlparse(path)
        params = urllib.parse.parse_qs(parsed.query)
        username = params.get("username", ["anonymous"])[0]

        self.waiting_queue.append((websocket, username))
        join_msg = json.dumps({"type": "join", "data": username})
        await self.broadcast_to_waiting(self.waiting_queue, join_msg)
        # print(f"[Tournament] {username} connected. Waiting: {len(self.waiting_queue)}")
        try:
            await websocket.wait_closed()
        finally:
            if self.game_start is False and (websocket, username) in self.waiting_queue:
                self.waiting_queue.remove((websocket, username))
                part_msg = json.dumps({"type": "part", "data": username})
                await self.broadcast_to_waiting(self.waiting_queue, part_msg)
                # print(f"[Tournament] {username} disconnected and removed.")
    
    async def start_match(self, player1, player2, match_id):
        match = PingPongMatch(player1, player2, match_id=match_id)
        asyncio.create_task(self.player_handler(player1, "", match, 1))
        asyncio.create_task(self.player_handler(player2, "", match, 2))
        winner = await match.run()
        # print(f"[{match_id}] Match finished. Winner: Player {winner}")
        return player1 if winner == 1 else player2

    async def matchmaker(self):
        while True:
            if len(self.waiting_queue) >= 4:
            # 4명의 플레이어를 꺼냅니다.
                p1 = self.waiting_queue.pop(0)
                p2 = self.waiting_queue.pop(0)
                p3 = self.waiting_queue.pop(0)
                p4 = self.waiting_queue.pop(0)
                for player in [p1, p2, p3, p4]:
                    if not player.websocker.open:
                        for player_check in [p1, p2, p3, p4]:
                            if player_check.websocket.open:
                                self.waiting_queue.insert(player_check)
                                break
                        continue

                self.game_start = True
                # print("[Tournament] Starting round 1 matches.")
                # 라운드1: 두 경기를 동시에 진행 (1:1)
                task1 = asyncio.create_task(self.start_match(p1, p2, "tournament_round1_match1"))
                task2 = asyncio.create_task(self.start_match(p3, p4, "tournament_round1_match2"))
                winner1 = await task1
                winner2 = await task2

                # 결승 진출 알림 전송
                final_msg = json.dumps({"type": "final_info", "player1": winner1.username, "player2": winner2.username })
                try:
                    for p in [p1, p2, p3, p4]:
                        if p.open:
                            self.send(final_msg)
                except:
                    pass

                watch_list = []
                for p in [p1, p2, p3, p4]:
                    if p is not winner1 and p is not winner2:
                        watch_list.append(p)

                # print("[Tournament] Starting final match.")
                final_match = PingPongMatch(winner1, winner2, "tournament_final", watch_list)
                asyncio.create_task(self.player_handler(winner1, "", final_match, 1))
                asyncio.create_task(self.player_handler(winner2, "", final_match, 2))
                await final_match.run()
                # print(f"[Tournament] Tournament finished. Final Winner: Player {final_winner}")
                for p in [p1, p2, p3, p4]:
                    try:
                        await p.close()
                    except:
                        pass
            await asyncio.sleep(0.1)