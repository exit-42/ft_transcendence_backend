import asyncio
import json
import random
import time
import math
from collections import namedtuple

PlayerInfo = namedtuple("PlayerInfo", ["websocket", "username", "imagePath", "winCnt", "loseCnt"])
GameResultInfo = namedtuple("GameResultInfo", ["winner", "player1_score", "player2_score"])

# ============================================
# 상수 및 게임 화면 관련 설정 (3D 좌표 체계)
# ============================================
GAME_WIDTH = 3          # x: -1.5 ~ 1.5
GAME_DEPTH = 6          # z: -3 ~ 3
# y는 공의 z좌표에 따라 아래의 공식으로 산출 (최소값 1.5 이상)

FPS = 30
FRAME_DURATION = 1 / FPS

PADDLE_SPEED = 0.1      # x축 이동량
PADDLE_WIDTH = 0.5      # 패들 너비 (중심 기준)
BALL_RADIUS = 0.05      # 공 반지름

# 플레이어의 고정 z 좌표
PLAYER1_Z = -3
PLAYER2_Z = 3

# ============================================
# PingPongMatch 클래스 (개별 경기 로직)
# ============================================
class PingPongMatch:
    def __init__(self, players, watch_list=[]):
        # players는 PlayerInfo namedtuple의 리스트입니다.
        self.player1_info = players[0]  # z = -3 (플레이어1)
        self.player2_info = players[1]  # z = 3  (플레이어2)
        self.watch_list = watch_list
        self.player1_score = 0
        self.player2_score = 0

        # 각 플레이어의 입력 메시지를 저장할 큐
        self.input_queues = {1: asyncio.Queue(), 2: asyncio.Queue()}
        self.game_over = False
        self.winner = None  # 게임 종료 후 승리자 (1 또는 2)

        # 공 위치 초기화
        self.init_ball_pos()

    def init_ball_pos(self):
        self.ball_pos = [0, 2, 0]  # [x, y, z]
        # 공의 x, z 속도 (속도 값은 새로운 좌표 체계에 맞게 작게 설정)
        self.ball_vel = [random.choice([-0.05, 0.05]), random.choice([-0.05, 0.05])]
        # 각 패들의 x 위치 (초기엔 중앙)
        self.paddle1_x = 0
        self.paddle2_x = 0
        # 마지막으로 공을 튕긴 플레이어의 z 좌표 (None이면 아직 없음)
        self.last_hit = None

    async def process_inputs(self):
        """각 플레이어 큐에 쌓인 입력 메시지를 처리하여 패들 위치 업데이트"""
        for player, queue in self.input_queues.items():
            while not queue.empty():
                try:
                    msg = await queue.get()
                    if msg.get("type") == "move":
                        direction = msg.get("dir")
                        if player == 1:
                            if direction == "left":
                                self.paddle1_x -= PADDLE_SPEED
                            elif direction == "right":
                                self.paddle1_x += PADDLE_SPEED
                            # x 좌표 범위: -1.5 ~ 1.5 (패들 너비를 고려)
                            self.paddle1_x = max(-1.5 + PADDLE_WIDTH/2,
                                                 min(1.5 - PADDLE_WIDTH/2, self.paddle1_x))
                        elif player == 2:
                            if direction == "left":
                                self.paddle2_x -= PADDLE_SPEED
                            elif direction == "right":
                                self.paddle2_x += PADDLE_SPEED
                            self.paddle2_x = max(-1.5 + PADDLE_WIDTH/2,
                                                 min(1.5 - PADDLE_WIDTH/2, self.paddle2_x))
                except asyncio.QueueEmpty:
                    break

    async def update_ball(self):
        """공의 위치 업데이트, 패들 충돌 및 득점 체크"""
        # 업데이트: x, z 좌표
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[2] += self.ball_vel[1]

        # 좌우 벽 충돌: x 방향 반전 (x 범위: -1.5 ~ 1.5)
        if self.ball_pos[0] <= -1.5 + BALL_RADIUS or self.ball_pos[0] >= 1.5 - BALL_RADIUS:
            self.ball_vel[0] *= -1

        # 패들과의 충돌 체크 (z 방향)
        # 플레이어1 (z = -3): 공이 플레이어1 방향으로 이동 중 (z 속도 음수)
        if self.ball_vel[1] < 0 and self.ball_pos[2] - BALL_RADIUS <= PLAYER1_Z:
            # 패들의 x 좌표 차이가 패들 폭 이내이면 충돌
            if abs(self.ball_pos[0] - self.paddle1_x) <= PADDLE_WIDTH/2:
                self.ball_vel[1] *= -1  # z 속도 반전
                self.last_hit = PLAYER1_Z
            else:
                self.player2_score += 1
                self.winner = 2
                await self.broadcast_set_result()
                self.init_ball_pos()
                await asyncio.sleep(3)
        # 플레이어2 (z = 3): 공이 플레이어2 방향으로 이동 중 (z 속도 양수)
        elif self.ball_vel[1] > 0 and self.ball_pos[2] + BALL_RADIUS >= PLAYER2_Z:
            if abs(self.ball_pos[0] - self.paddle2_x) <= PADDLE_WIDTH/2:
                self.ball_vel[1] *= -1  # z 속도 반전
                self.last_hit = PLAYER2_Z
            else:
                self.player1_score += 1
                self.winner = 1
                await self.broadcast_set_result()
                self.init_ball_pos()
                await asyncio.sleep(3)

        # 공의 y 좌표 업데이트 (규칙에 따른 공식 적용)
        # 플레이어로부터 튕긴 직후부터 (z와 플레이어의 거리 4.5 이하)에는:
        if self.last_hit is None or abs(self.ball_pos[2] - self.last_hit) <= 4.5:
            self.ball_pos[1] = abs(math.cos(math.pi/3 * self.ball_pos[2])) + 1
        else:
            # 마지막 튕긴 플레이어에 따라 두 가지 경우
            if self.last_hit == PLAYER1_Z and self.ball_vel[1] > 0:  # 공이 z 방향으로 증가
                self.ball_pos[1] = abs(math.cos(math.pi/9 * (self.ball_pos[2] - 3))) + 1
            elif self.last_hit == PLAYER2_Z and self.ball_vel[1] < 0:  # 공이 z 방향으로 감소
                self.ball_pos[1] = abs(math.cos(math.pi/9 * (self.ball_pos[2] - 6))) + 1
            else:
                # 기본 공식
                self.ball_pos[1] = abs(math.cos(math.pi/3 * self.ball_pos[2])) + 1

        # 게임 종료 조건 (예: 5점 도달 시)
        if self.player1_score >= 5:
            self.winner = 1
            self.game_over = True
        elif self.player2_score >= 5:
            self.winner = 2
            self.game_over = True

    async def broadcast_state(self):
        """현재 게임 상태를 play DTO로 클라이언트에 전송 (30fps)"""
        # 각 플레이어에게는 자신의 패들 정보를 첫번째로 보내도록 순서를 조정
        ball_pos_rounded = [round(coord, 4) for coord in self.ball_pos]
        state1 = {
            "type": "play",
            "ball": ball_pos_rounded,  # [x, y, z]
            "player": [
                self.paddle1_x,
                self.paddle2_x
            ],
        }
        msg1 = json.dumps(state1)
        state2 = {
            "type": "play",
            "ball": ball_pos_rounded,  # [x, y, z]
            "player": [
                self.paddle2_x,
                self.paddle1_x
            ],
        }
        msg2 = json.dumps(state2)
        try:
            await self.player1_info.websocket.send(msg1)
            await self.player2_info.websocket.send(msg2)
        except Exception as e:
            self.game_over = True

        for watcher in self.watch_list:
            try:
                await watcher.websocket.send(msg1)
            except:
                pass

    async def broadcast_set_result(self):
        """한 세트 결과를 result DTO로 전송"""
        if self.winner == 1:
            result = {
                "type": "set_result",
                "win": self.player1_info.username,
                "lose": self.player2_info.username,
            }
        else:
            result = {
                "type": "set_result",
                "win": self.player2_info.username,
                "lose": self.player1_info.username,
            }
        msg = json.dumps(result)
        try:
            await self.player1_info.websocket.send(msg)
            await self.player2_info.websocket.send(msg)
            for watcher in self.watch_list:
                await watcher.websocket.send(msg)
        except Exception as e:
            pass

    async def broadcast_match_result(self):
        """최종 게임 결과를 result DTO로 전송"""
        if self.winner == 1:
            result = {
                "type": "match_result",
                "win": self.player1_info.username,
                "lose": self.player2_info.username,
                "win_cnt": self.player1_score,
                "lose_cnt": self.player2_score,
            }
        else:
            result = {
                "type": "match_result",
                "win": self.player2_info.username,
                "lose": self.player1_info.username,
                "win_cnt": self.player2_score,
                "lose_cnt": self.player1_score,
            }
        msg = json.dumps(result)
        for websocket in [self.player1_info.websocket, self.player2_info.websocket] \
            + [w.websocket for w in self.watch_list]:
            try:
                await websocket.send(msg)
            except Exception:
                pass

    async def game_loop(self):
        """30fps 루프: 입력 처리 → 상태 업데이트 → play 메시지 브로드캐스트"""
        while not self.game_over:
            start_time = time.time()
            await self.process_inputs()
            await self.update_ball()
            if self.game_over is False:
                await self.broadcast_state()
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, FRAME_DURATION - elapsed))
        await self.broadcast_match_result()

    async def run(self):
        msg = {
            "type": "start",
        }
        msg_json = json.dumps(msg)
        try:
            await self.player1_info.websocket.send(msg_json)
            await self.player2_info.websocket.send(msg_json)
            for watcher in self.watch_list:
                await watcher.websocket.send(msg)
        except Exception:
            pass
        await asyncio.sleep(5)
        await self.game_loop()
        winner_info = self.player1_info if self.winner == 1 else self.player2_info
        result = GameResultInfo(
            winner=winner_info,
            player1_score=self.player1_score,
            player2_score=self.player2_score,
        )
        return result
