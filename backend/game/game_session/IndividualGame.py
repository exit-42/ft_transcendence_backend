import IGame
import PingPongMatch
import asyncio
import json
import urllib.parse

class individual(IGame):
    
    async def register(self, websocket, path):
        # URL 쿼리에서 username 추출 (없으면 anonymous)
        parsed = urllib.parse.urlparse(path)
        params = urllib.parse.parse_qs(parsed.query)
        username = params.get("username", ["anonymous"])[0]

        self.waiting_queue.append((websocket, username))
        join_msg = json.dumps({"type": "join", "data": username})
        await self.broadcast_to_waiting(self.waiting_queue, join_msg)
        # print(f"[Individual] {username} connected. Waiting: {len(self.waiting_queue)}")
        try:
            await websocket.wait_closed()
        finally:
            # 연결 해제 시 대기 리스트에서 제거하고 part 메시지 브로드캐스트
            if self.game_start is False and (websocket, username) in self.waiting_queue:
                self.waiting_queue.remove((websocket, username))
                part_msg = json.dumps({"type": "part", "data": username})
                await self.broadcast_to_waiting(self.waiting_queue, part_msg)
                # print(f"[Individual] {username} disconnected and removed.")
    
    async def start_match(self, player1, player2):
        match = PingPongMatch(player1, player2, match_id="individual")
        asyncio.create_task(self.player_handler(player1, match, 1))
        asyncio.create_task(self.player_handler(player2, match, 2))
        winner = await match.run()
        # print(f"[Individual] Match finished. Winner: Player {winner}")

    async def matchmaker(self):
        while True:
            if len(self.waiting_queue) >= 4:
            # 4명의 플레이어를 꺼냅니다.
                p1 = self.waiting_queue.pop(0)
                p2 = self.waiting_queue.pop(0)
                for player in [p1, p2]:
                    if not player.websocker.open:
                        for player_check in [p1, p2]:
                            if player_check.websocket.open:
                                self.waiting_queue.insert(player_check)
                                break
                        continue
            if len(self.waiting_queue) >= 2:
                # 대기 중인 플레이어 2명을 꺼내서 경기를 시작합니다.
                p1 = self.waiting_queue.pop(0)
                p2 = self.waiting_queue.pop(0)
                # print("[Individual] Starting a match.")
                self.game_start = True
                asyncio.create_task(self.start_match(p1, p2))
                for p in [p1, p2]:
                    try:
                        await p.close()
                    except:
                        pass
            await asyncio.sleep(0.1)