import IGame
import PingPongMatch
import asyncio
import json

class TournamentGame(IGame):
    async def register(self, websocket, path):
        self.waiting_queue.append(websocket)
        print(f"[Tournament] Player connected. Waiting: {len(self.waiting_queue)}")
        try:
            asyncio.create_task(self.matchmaker())
            await websocket.wait_closed()
        finally:
            if websocket in self.waiting_queue:
                self.waiting_queue.remove(websocket)
                print("[Tournament] Player disconnected and removed from waiting list.")
    
    async def start_match(self, player1, player2, match_id):
        match = PingPongMatch(player1, player2, match_id=match_id)
        asyncio.create_task(self.player_handler(player1, "", match, 1))
        asyncio.create_task(self.player_handler(player2, "", match, 2))
        winner = await match.run()
        print(f"[{match_id}] Match finished. Winner: Player {winner}")
        return player1 if winner == 1 else player2

    async def matchmaker(self):
        if len(self.waiting_queue) >= 4:
        # 4명의 플레이어를 꺼냅니다.
            p1 = self.waiting_queue.pop(0)
            p2 = self.waiting_queue.pop(0)
            p3 = self.waiting_queue.pop(0)
            p4 = self.waiting_queue.pop(0)
            # 연결 상태 확인 (끊어진 플레이어가 있으면 다시 대기열에 넣음)
            for p in [p1, p2, p3, p4]:
                if not p.open:
                    for player in [p1, p2, p3, p4]:
                        if player.open:
                            self.waiting_queue.insert(0, player)

            print("[Tournament] Starting round 1 matches.")
            # 라운드1: 두 경기를 동시에 진행 (1:1)
            task1 = asyncio.create_task(self.start_match(p1, p2, "tournament_round1_match1"))
            task2 = asyncio.create_task(self.start_match(p3, p4, "tournament_round1_match2"))
            winner1 = await task1
            winner2 = await task2

            # 결승 진출 알림 전송
            final_msg = json.dumps({"info": "Final match starting"})
            try:
                await asyncio.gather(winner1.send(final_msg), winner2.send(final_msg))
            except:
                pass

            print("[Tournament] Starting final match.")
            final_match = PingPongMatch(winner1, winner2, match_id="tournament_final")
            asyncio.create_task(self.player_handler(winner1, "", final_match, 1))
            asyncio.create_task(self.player_handler(winner2, "", final_match, 2))
            final_winner = await final_match.run()
            print(f"[Tournament] Tournament finished. Final Winner: Player {final_winner}")
            try:
                await winner1.close()
            except:
                pass
            try:
                await winner2.close()
            except:
                pass

