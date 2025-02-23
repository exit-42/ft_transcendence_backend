import asyncio
import json
import random
import time
from collections import namedtuple

PlayerInfo = namedtuple("PlayerInfo", ["websocket", "user_id", "username"])
GameResultInfo = namedtuple(
    "GameResultInfo", ["winner", "player1_score", "player2_score"]
)

# ============================================
# 상수 및 게임 화면 관련 설정
# ============================================
GAME_WIDTH = 800
GAME_HEIGHT = 600
FPS = 30
FRAME_DURATION = 1 / FPS

PADDLE_SPEED = 10  # 키 입력당 이동량
PADDLE_WIDTH = 100  # 패들 너비 (중심 기준)
PADDLE_Y_OFFSET = 30  # 패들이 화면 가장자리에서 떨어진 거리
BALL_RADIUS = 10  # 공 반지름


# ============================================
# PingPongMatch 클래스 (개별 경기 로직)
# ============================================
class PingPongMatch:
    def __init__(self, players, match_id="", watch_list=[]):
        # players는 이제 PlayerInfo namedtuple의 리스트로 받습니다.
        self.player1_info = players[0]  # 하단 패들 (플레이어 1): PlayerInfo namedtuple
        self.player2_info = players[1]  # 상단 패들 (플레이어 2): PlayerInfo namedtuple
        self.watch_list = watch_list
        self.player1_score = 0
        self.player2_score = 0
        self.match_id = match_id

        # 각 플레이어의 입력 메시지를 저장할 큐
        self.input_queues = {1: asyncio.Queue(), 2: asyncio.Queue()}
        self.game_over = False
        self.winner = None  # 게임 종료 후 승리자 (1 또는 2)

        # 초기 상태: 공은 중앙에서 시작하며 임의 방향으로 이동
        self.ball_pos = [GAME_WIDTH / 2, GAME_HEIGHT / 2]  # [x, y] (y를 z처럼 사용)
        self.ball_vel = [random.choice([-5, 5]), random.choice([-5, 5])]
        # 각 패들의 x 위치 (초기엔 중앙)
        self.paddle1_x = GAME_WIDTH / 2
        self.paddle2_x = GAME_WIDTH / 2

    async def process_inputs(self):
        """각 플레이어 큐에 쌓인 입력 메시지를 처리하여 패들 위치 업데이트"""
        for player, queue in self.input_queues.items():
            while not queue.empty():
                try:
                    msg = (
                        await queue.get()
                    )  # Changed to await queue.get() for async queue
                    if msg.get("action") == "move":
                        direction = msg.get("direction")
                        if player == 1:
                            if direction == "left":
                                self.paddle1_x -= PADDLE_SPEED
                            elif direction == "right":
                                self.paddle1_x += PADDLE_SPEED
                            self.paddle1_x = max(
                                PADDLE_WIDTH / 2,
                                min(GAME_WIDTH - PADDLE_WIDTH / 2, self.paddle1_x),
                            )
                        elif player == 2:
                            if direction == "left":
                                self.paddle2_x -= PADDLE_SPEED
                            elif direction == "right":
                                self.paddle2_x += PADDLE_SPEED
                            self.paddle2_x = max(
                                PADDLE_WIDTH / 2,
                                min(GAME_WIDTH - PADDLE_WIDTH / 2, self.paddle2_x),
                            )
                except asyncio.QueueEmpty:
                    break

    async def update_ball(self):
        """공의 위치 업데이트, 패들 충돌 및 골 체크"""
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[1] += self.ball_vel[1]

        # 좌우 벽 충돌: x 방향 반전
        if (
            self.ball_pos[0] <= BALL_RADIUS
            or self.ball_pos[0] >= GAME_WIDTH - BALL_RADIUS
        ):
            self.ball_vel[0] *= -1

        # 하단(플레이어1) 패들 충돌 체크 (공이 내려가는 경우)
        if self.ball_vel[1] > 0:
            paddle_y = GAME_HEIGHT - PADDLE_Y_OFFSET
            if self.ball_pos[1] + BALL_RADIUS >= paddle_y:
                if abs(self.ball_pos[0] - self.paddle1_x) <= PADDLE_WIDTH / 2:
                    self.ball_vel[1] *= -1
                else:
                    self.player2_score += 1
                    self.winner = 2
                    await self.broadcast_result()  # Added await for async method
                    await asyncio.sleep(1)
        # 상단(플레이어2) 패들 충돌 체크 (공이 올라가는 경우)
        elif self.ball_vel[1] < 0:
            paddle_y = PADDLE_Y_OFFSET
            if self.ball_pos[1] - BALL_RADIUS <= paddle_y:
                if abs(self.ball_pos[0] - self.paddle2_x) <= PADDLE_WIDTH / 2:
                    self.ball_vel[1] *= -1
                else:
                    self.player1_score += 1
                    self.winner = 1
                    await self.broadcast_result()  # Added await for async method
                    await asyncio.sleep(1)
        # 게임 종료 조건 (5점)
        if self.player1_score >= 5:
            self.winner = 1
            self.game_over = True
        elif self.player2_score >= 5:  # Corrected to >= 5 for game over condition
            self.winner = 2
            self.game_over = True

    async def broadcast_state(self):
        """현재 게임 상태를 play DTO로 클라이언트에 전송 (30fps)"""
        state1 = {
            "type": "play",
            "ball": self.ball_pos,  # [x, y] → [x, z]
            "player": [self.paddle1_x, self.paddle2_x],
        }
        msg1 = json.dumps(state1)
        state2 = {
            "type": "play",
            "ball": self.ball_pos,  # [x, y] → [x, z]
            "player": [self.paddle2_x, self.paddle1_x],
        }
        msg2 = json.dumps(state2)
        try:
            await self.player1_info.websocket.send(msg1)
            await self.player2_info.websocket.send(msg2)
        except Exception as e:
            self.game_over = True

        for watcher in self.watch_list:
            try:
                await watcher[0].send(
                    msg1
                )  # Added await for websocket send and access websocket from tuple
            except:
                pass

    async def broadcast_result(self):
        """게임 결과를 result DTO로 전송"""
        if self.winner == 1:
            result = {
                "type": "result",
                "win": self.player1_info.username,
                "lose": self.player2_info.username,
            }
        else:
            result = {
                "type": "result",
                "win": self.player2_info.username,
                "lose": self.player1_info.username,
            }
        msg = json.dumps(result)
        try:
            await self.player1_info.websocket.send(msg)
            await self.player2_info.websocket.send(msg)
            for watcher in self.watch_list:
                await watcher[0].send(
                    msg
                )  # Added await for websocket send and access websocket from tuple
        except Exception as e:
            pass

    async def game_loop(self):
        """30fps 루프: 입력 처리 → 상태 업데이트 → play 메시지 브로드캐스트"""
        while not self.game_over:
            start_time = time.time()
            await self.process_inputs()
            await self.update_ball()  # Added await for async method
            await self.broadcast_state()  # Added await for async method
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, FRAME_DURATION - elapsed))

    async def run(self):
        await self.game_loop()
        winner_info = None
        if self.winner == 1:
            winner_info = self.player1_info
        else:
            winner_info = self.player2_info
        result = GameResultInfo(
            winner=winner_info,
            player1_score=self.player1_score,
            player2_score=self.player2_score,
        )
        return result
