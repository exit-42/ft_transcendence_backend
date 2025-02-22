import asyncio
import json
import random
import time
import argparse
import websockets

# ============================================
# 상수 및 게임 화면 관련 설정
# ============================================
GAME_WIDTH = 800
GAME_HEIGHT = 600
FPS = 30
FRAME_DURATION = 1 / FPS

PADDLE_SPEED = 10           # 패들 이동 속도(키 입력당 이동량)
PADDLE_WIDTH = 100          # 패들 너비 (중심 기준)
PADDLE_Y_OFFSET = 30        # 패들이 화면 가장자리에서 떨어진 거리
BALL_RADIUS = 10            # 공의 반지름

# ============================================
# PingPongMatch 클래스 (개별 경기 로직)
# ============================================
class PingPongMatch:
    def __init__(self, player1_ws, player2_ws, match_id=""):
        self.player1_ws = player1_ws  # 하단 패들 (플레이어 1)
        self.player2_ws = player2_ws  # 상단 패들 (플레이어 2)
        self.match_id = match_id

        # 각 플레이어의 입력 메시지를 저장할 큐
        self.input_queues = {1: asyncio.Queue(), 2: asyncio.Queue()}
        self.game_over = False
        self.winner = None  # 게임 종료 후 승리자 (1 또는 2)

        # 초기 상태: 공은 중앙에서 시작하며, 임의 방향으로 이동
        self.ball_pos = [GAME_WIDTH / 2, GAME_HEIGHT / 2]
        self.ball_vel = [random.choice([-5, 5]), random.choice([-5, 5])]
        # 각 패들의 x 위치 (초기엔 중앙)
        self.paddle1_x = GAME_WIDTH / 2
        self.paddle2_x = GAME_WIDTH / 2

    async def process_inputs(self):
        """각 플레이어 큐에 쌓인 입력 메시지를 처리하여 패들 위치 업데이트"""
        for player, queue in self.input_queues.items():
            while not queue.empty():
                try:
                    msg = queue.get_nowait()
                    if msg.get("action") == "move":
                        direction = msg.get("direction")
                        if player == 1:
                            if direction == "left":
                                self.paddle1_x -= PADDLE_SPEED
                            elif direction == "right":
                                self.paddle1_x += PADDLE_SPEED
                            self.paddle1_x = max(PADDLE_WIDTH / 2, min(GAME_WIDTH - PADDLE_WIDTH / 2, self.paddle1_x))
                        elif player == 2:
                            if direction == "left":
                                self.paddle2_x -= PADDLE_SPEED
                            elif direction == "right":
                                self.paddle2_x += PADDLE_SPEED
                            self.paddle2_x = max(PADDLE_WIDTH / 2, min(GAME_WIDTH - PADDLE_WIDTH / 2, self.paddle2_x))
                except asyncio.QueueEmpty:
                    break

    def update_ball(self):
        """공의 위치 업데이트, 패들 충돌 및 골 체크"""
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[1] += self.ball_vel[1]

        # 좌우 벽 충돌: x 방향 반전
        if self.ball_pos[0] <= BALL_RADIUS or self.ball_pos[0] >= GAME_WIDTH - BALL_RADIUS:
            self.ball_vel[0] *= -1

        # 하단(플레이어1) 패들 충돌 체크 (공이 내려가는 경우)
        if self.ball_vel[1] > 0:
            paddle_y = GAME_HEIGHT - PADDLE_Y_OFFSET
            if self.ball_pos[1] + BALL_RADIUS >= paddle_y:
                if abs(self.ball_pos[0] - self.paddle1_x) <= PADDLE_WIDTH / 2:
                    self.ball_vel[1] *= -1  # 충돌 시 y 방향 반전
                else:
                    self.game_over = True
                    self.winner = 2  # 패들을 놓쳤으므로 플레이어2 승리
        # 상단(플레이어2) 패들 충돌 체크 (공이 올라가는 경우)
        elif self.ball_vel[1] < 0:
            paddle_y = PADDLE_Y_OFFSET
            if self.ball_pos[1] - BALL_RADIUS <= paddle_y:
                if abs(self.ball_pos[0] - self.paddle2_x) <= PADDLE_WIDTH / 2:
                    self.ball_vel[1] *= -1
                else:
                    self.game_over = True
                    self.winner = 1

    async def broadcast_state(self):
        """현재 게임 상태(공의 위치, 패들 위치, 게임 종료 여부, 승자)를 클라이언트에 전송"""
        state = {
            "ball_pos": self.ball_pos,
            "paddle1_x": self.paddle1_x,
            "paddle2_x": self.paddle2_x,
            "game_over": self.game_over,
            "winner": self.winner,
        }
        msg = json.dumps(state)
        try:
            await asyncio.gather(
                self.player1_ws.send(msg),
                self.player2_ws.send(msg)
            )
        except Exception as e:
            self.game_over = True

    async def game_loop(self):
        """30fps 루프: 입력 처리 → 상태 업데이트 → 브로드캐스트"""
        while not self.game_over:
            start_time = time.time()
            await self.process_inputs()
            self.update_ball()
            await self.broadcast_state()
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, FRAME_DURATION - elapsed))
        await self.broadcast_state()

    async def run(self):
        """경기 실행 후 승리자 반환"""
        await self.game_loop()
        return self.winner

# ============================================
# 플레이어 소켓에서 입력 메시지 처리
# ============================================
async def player_handler(websocket, path, match, player_number):
    """
    각 플레이어 소켓에서 들어오는 메시지를 읽어 해당 플레이어 큐(match.input_queues)에 저장
    """
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                await match.input_queues[player_number].put(data)
            except json.JSONDecodeError:
                continue
    except websockets.exceptions.ConnectionClosed:
        print(f"[{match.match_id}] Player {player_number} disconnected")
        match.game_over = True
        match.winner = 2 if player_number == 1 else 1

# ============================================
# 대기 리스트 및 매치메이커 (개인전 / 토너먼트)
# ============================================
waiting_individual = []
waiting_tournament = []

# -- 클라이언트 등록 함수 --
async def register_individual(websocket, path):
    """
    클라이언트가 연결되면 대기 리스트에 추가하고,
    경기 시작 전(또는 중) 클라이언트가 나가면 자동 제거
    """
    waiting_individual.append(websocket)
    print(f"[Individual] Player connected. Waiting: {len(waiting_individual)}")
    try:
        asyncio.create_task(individual_matchmaker(""))
        await websocket.wait_closed()
    finally:
        if websocket in waiting_individual:
            waiting_individual.remove(websocket)
            print("[Individual] Player disconnected and removed from waiting list.")

async def register_tournament(websocket, path):
    waiting_tournament.append(websocket)
    print(f"[Tournament] Player connected. Waiting: {len(waiting_tournament)}")
    try:
        asyncio.create_task(tournament_matchmaker())
        await websocket.wait_closed()
    finally:
        if websocket in waiting_tournament:
            waiting_tournament.remove(websocket)
            print("[Tournament] Player disconnected and removed from waiting list.")

# -- 매치메이커 함수: 대기 리스트에 정원이 채워지면 경기 시작 --
async def individual_matchmaker(path):
    if len(waiting_individual) >= 2:
        # 대기 중인 플레이어 2명을 꺼내서 경기를 시작합니다.
        p1 = waiting_individual.pop(0)
        p2 = waiting_individual.pop(0)
        if not (p1.open and p2.open):
            # 연결이 끊긴 플레이어가 있다면 재조정
            if p1.open:
                waiting_individual.insert(0, p1)
            if p2.open:
                waiting_individual.insert(0, p2)
        print("[Individual] Starting a match.")
        asyncio.create_task(start_individual_match(p1, p2, path))

async def start_individual_match(player1, player2, path):
    match = PingPongMatch(player1, player2, match_id="individual")
    asyncio.create_task(player_handler(player1, path, match, 1))
    asyncio.create_task(player_handler(player2, path, match, 2))
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

async def tournament_matchmaker():
    if len(waiting_tournament) >= 4:
        # 4명의 플레이어를 꺼냅니다.
        p1 = waiting_tournament.pop(0)
        p2 = waiting_tournament.pop(0)
        p3 = waiting_tournament.pop(0)
        p4 = waiting_tournament.pop(0)
        # 연결 상태 확인 (끊어진 플레이어가 있으면 다시 대기열에 넣음)
        for p in [p1, p2, p3, p4]:
            if not p.open:
                for player in [p1, p2, p3, p4]:
                    if player.open:
                        waiting_tournament.insert(0, player)

        print("[Tournament] Starting round 1 matches.")
        # 라운드1: 두 경기를 동시에 진행 (1:1)
        task1 = asyncio.create_task(start_tournament_match(p1, p2, "tournament_round1_match1"))
        task2 = asyncio.create_task(start_tournament_match(p3, p4, "tournament_round1_match2"))
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
        asyncio.create_task(player_handler(winner1, "", final_match, 1))
        asyncio.create_task(player_handler(winner2, "", final_match, 2))
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

async def start_tournament_match(player1, player2, match_id):
    match = PingPongMatch(player1, player2, match_id=match_id)
    asyncio.create_task(player_handler(player1, "", match, 1))
    asyncio.create_task(player_handler(player2, "", match, 2))
    winner = await match.run()
    print(f"[{match_id}] Match finished. Winner: Player {winner}")
    return player1 if winner == 1 else player2

# ============================================
# 메인 서버: 모드에 따라 소켓 서버 및 매치메이커 실행
# ============================================
async def main_server(mode, port):
    if mode == "individual":
        print(f"Starting individual match server on port {port}")
        # 매치메이커 태스크 시작
        asyncio.create_task(individual_matchmaker(""))
        server = await websockets.serve(register_individual, "0.0.0.0", port)
    elif mode == "tournament":
        print(f"Starting tournament server on port {port}")
        asyncio.create_task(tournament_matchmaker())
        server = await websockets.serve(register_tournament, "0.0.0.0", port)
    else:
        print("Unknown mode")
        return
    await server.wait_closed()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["individual", "tournament"], required=True,
                        help="게임 모드: 1:1 개인전 또는 4인 토너먼트")
    parser.add_argument("--port", type=int, default=8765, help="서버 포트")
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(main_server(args.mode, args.port))
