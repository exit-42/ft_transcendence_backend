import IGame
import PingPongMatch
import asyncio
import json

class IndividualGame(IGame):

    async def register(self, websocket, path):
        """
        클라이언트가 연결되면 대기 리스트에 추가하고,
        경기 시작 전(또는 중) 클라이언트가 나가면 자동 제거
        """
        self.waiting_queue.append(websocket)
        print(f"[Individual] Player connected. Waiting: {len(self.waiting_queue)}")
        try:
            asyncio.create_task(self.individual_matchmaker(""))
            await websocket.wait_closed()
        finally:
            if websocket in self.waiting_queue:
                self.waiting_queue.remove(websocket)
                print("[Individual] Player disconnected and removed from waiting list.")
    
    async def start_match(self, player1, player2):
        match = PingPongMatch(player1, player2, match_id="individual")
        asyncio.create_task(self.player_handler(player1, match, 1))
        asyncio.create_task(self.player_handler(player2, match, 2))
        winner = await match.run()
        print(f"[Individual] Match finished. Winner: Player {winner}")
        try:
            await player1.close()
        except:
            pass
        try:
            await player2.close()
        except:
            pass

    async def matchmaker(self):
        if len(self.waiting_queue) >= 2:
            # 대기 중인 플레이어 2명을 꺼내서 경기를 시작합니다.
            p1 = self.waiting_queue.pop(0)
            p2 = self.waiting_queue.pop(0)
            if not (p1.open and p2.open):
                # 연결이 끊긴 플레이어가 있다면 재조정
                if p1.open:
                    self.waiting_queue.insert(0, p1)
                if p2.open:
                    self.waiting_queue.insert(0, p2)
            print("[Individual] Starting a match.")
            asyncio.create_task(self.start_match(p1, p2))
