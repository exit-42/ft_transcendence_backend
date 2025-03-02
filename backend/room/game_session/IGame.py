import asyncio
import json
import websockets
import urllib.parse
from abc import *
import os
from .PingPongMatch import *
import sys


class IGame(metaclass=ABCMeta):
    def __init__(self, room_id):
        self.waiting_queue = []
        self.room_id = room_id
        self.game_start = False
        self.system = None

    @classmethod
    async def create(cls, room_id):
        instance = cls(room_id)
        await instance.connect_to_websocket()  # 웹소켓 연결 완료를 보장
        return instance

    async def connect_to_websocket(self):
        uri = os.getenv("DJANGO_WEBSOCKET_URI")
        # self.system = await websockets.connect(uri)
        self.system = await websockets.connect(
            uri, additional_headers={"Origin": "ws://127.0.0.1"}
        )

    @abstractmethod
    async def matchmaker():
        pass

    async def player_handler(self, websocket, match, player_number):
        """
        각 플레이어 소켓에서 들어오는 메시지를 읽어 해당 플레이어 큐(match.input_queues)에 저장
        """
        TIMEOUT_DURATION = 0.1  # 타임아웃 시간 (초) - 필요에 따라 조정
        try:
            while not match.game_over:
                try:
                    # message = await websocket.recv()
                    message = await asyncio.wait_for(
                        websocket.recv(), timeout=TIMEOUT_DURATION
                    )
                    data = json.loads(message)
                    await match.input_queues[player_number].put(data)
                except json.JSONDecodeError:
                    continue
                except asyncio.TimeoutError:
                    # 타임아웃 발생: 메시지 없음, 게임 오버 상태 확인 후 루프 계속
                    continue  # 혹은 필요하다면 match.game_over 상태를 여기서 다시 체크하고 break 가능
        except websockets.exceptions.ConnectionClosed:
            if match.game_over == False:
                match.game_over = True
                if player_number == 1:
                    match.winner = 2
                    match.player2_score = 5
                else:
                    match.winner = 1
                    match.player2_score = 5

    async def broadcast_to_waiting(self, message):
        for player in self.waiting_queue:
            try:
                await player.websocket.send(message)
            except:
                pass

    async def register(self, websocket):
        username = None
        parsed = urllib.parse.urlparse(websocket.request.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "username" in params:
            username = params.get("username")[0]

        if not username:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        # 후보군 처리: 우선 system 소켓에 part 메시지 전송
        candidate_msg = json.dumps(
            {"type": "join", "room_id": self.room_id, "player": username}
        )
        await self.system.send(candidate_msg)

        # system 소켓으로부터 success 메시지 수신 (여기서 imagePath, winCnt, loseCnt 포함)
        success_msg = await self.system.recv()
        success_data = json.loads(success_msg)
        if success_data.get("type") == "success":
            imagePath = success_data.get("img_path")
            winCnt = success_data.get("winCnt")
            loseCnt = success_data.get("loseCnt")
            # 새로 받은 필드를 포함하여 PlayerInfo 생성
            player_info = PlayerInfo(
                websocket=websocket,
                username=username,
                imagePath=imagePath,
                winCnt=winCnt,
                loseCnt=loseCnt,
            )
            self.waiting_queue.append(player_info)
            # 모든 플레이어에게 대기열 업데이트 알림 (플레이어 별 정보 전송)
            updated_queue_msg = json.dumps(
                {
                    "type": "join",
                    "data": {
                        player.username: {
                            "img_path": player.imagePath,
                            "winCnt": player.winCnt,
                            "loseCnt": player.loseCnt,
                        }
                        for player in self.waiting_queue
                    },
                }
            )
            await self.broadcast_to_waiting(updated_queue_msg)
        else:
            # success 메시지가 아닌 경우 연결 종료
            await websocket.close(code=1011, reason="Registration failed")
            return

        try:
            await websocket.wait_closed()
        finally:
            # 연결 종료 시 waiting_queue에서 제거 및 전체 대기열 업데이트 전송
            if self.game_start is False and player_info in self.waiting_queue:
                exit_msg = json.dumps(
                    {"type": "exit", "room_id": self.room_id, "player": username}
                )
                await self.system.send(exit_msg)
                system_msg = await self.system.recv()
                system_res = json.loads(system_msg)
                if system_res.get("type") == "error":
                    print("fatal error!!!!")
                    sys.exit(1)
                self.waiting_queue.remove(player_info)
                updated_queue_msg = json.dumps(
                    {
                        "type": "join",
                        "data": {
                            player.username: {
                                "img_path": player.imagePath,
                                "winCnt": player.winCnt,
                                "loseCnt": player.loseCnt,
                            }
                            for player in self.waiting_queue
                        },
                    }
                )
                await self.broadcast_to_waiting(updated_queue_msg)

    async def send_log(self, result, player1_info, player2_info, rank):
        msg = {
            "type": "result",
            "room_id": self.room_id,
            "player_A_name": player1_info.username,
            "player_B_name": player2_info.username,
            "score_A": result.player1_score,
            "score_B": result.player2_score,
            "rank": rank,
        }
        json_msg = json.dumps(msg)
        await self.system.send(json_msg)
