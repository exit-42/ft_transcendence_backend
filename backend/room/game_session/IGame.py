import asyncio
import json
import websockets
import urllib.parse
from abc import *
import os
import jwt
from .PingPongMatch import *


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
            uri,
            additional_headers={"Origin": "ws://127.0.0.1"}
        )

    @abstractmethod
    async def matchmaker():
        pass

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

    async def broadcast_to_waiting(self, waiting_list, message):
        for ws, _ in self.waiting_queue:
            try:
                await ws.send(message)
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
        candidate_msg = json.dumps({"type": "join", "room_id": self.room_id, "player": username})
        await self.system.send(candidate_msg)

        # system 소켓으로부터 success 메시지를 대기
        success_msg = await self.system.recv()
        success_data = json.loads(success_msg)
        if success_data.get("type") == "success":
            # 성공 메시지를 받으면 waiting_queue에 최종적으로 추가
            player_info = PlayerInfo(websocket=websocket, username=username)
            self.waiting_queue.append(player_info)
            # 전체 대기열 정보를 플레이어들에게 전송 (queue에 있는 모든 username 리스트)
            queue_usernames = [p.username for p in self.waiting_queue]
            updated_queue_msg = json.dumps({"type": "part", "data": queue_usernames})
            await self.broadcast_to_waiting(self.waiting_queue, updated_queue_msg)
        else:
            # success 메시지가 아니면 연결 종료
            await websocket.close(code=1011, reason="Registration failed")
            return

        try:
            await websocket.wait_closed()
        finally:
            # 연결 종료 시 waiting_queue에서 제거하고 전체 queue 업데이트 전송
            if self.game_start is False and player_info in self.waiting_queue:
                self.waiting_queue.remove(player_info)
                queue_usernames = [p.username for p in self.waiting_queue]
                updated_queue_msg = json.dumps({"type": "part", "data": queue_usernames})
                await self.broadcast_to_waiting(self.waiting_queue, updated_queue_msg)

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
