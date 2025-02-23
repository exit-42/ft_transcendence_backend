import asyncio
import json
import websockets
import urllib.parse
from websockets import WebSocketServerProtocol
from abc import *
import os
import jwt
from PingPongMatch import *

class IGame(metaclass=ABCMeta):
    def __init__(self):
        self.waiting_queue = []
        self.game_start = False
        self.system = None
        self.connect_to_websocket()

    async def connect_to_websocket(self):
        uri = os.getenv("DJANGO_WEBSOCKET_URI")
        self.system = await websockets.connect(uri)
        if self.system.close:
            raise Exception('cannot connect with main server')

    @abstractmethod
    async def start_individual_match(player1, player2, path):
        pass

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
    
    async def register(self, websocket: WebSocketServerProtocol, path: str):
        cookies = websocket.request_headers.get("Cookie", "")
        jwt_token = None
        for cookie in cookies.split("; "):
            if cookie.startswith("jwt="):
                jwt_token = cookie.split("=")[1]
                break

        user_id = None
        if jwt_token:
            secret_key = os.getenv("SECRET_KEY")
            try:
                decoded = jwt.decode(jwt_token, secret_key, algorithms=["HS256"])
                user_id = decoded.get("user_id")
            except jwt.ExpiredSignatureError:
                pass
            except jwt.InvalidTokenError:
                pass

        username = None
        parsed = urllib.parse.urlparse(path)
        params = urllib.parse.parse_qs(parsed.query)
        if "username" in params: # handle case when username is missing
            username = params.get("username")[0]

        if not user_id or not username:  # If user_id or username is missing, close the connection
            await websocket.close(code=1008, reason="Unauthorized")  # Close with a policy violation code
            return

        # 대기열에 추가
        player_info = PlayerInfo(websocket=websocket, user_id=user_id, username=username)
        self.waiting_queue.append(player_info)
        join_msg = json.dumps({"type": "join", "data": username})
        await self.broadcast_to_waiting(self.waiting_queue, join_msg)

        try:
            await websocket.wait_closed()
        finally:
            if self.game_start is False and player_info in self.waiting_queue:
                self.waiting_queue.remove(player_info)
                part_msg = json.dumps({"type": "part", "data": username})
                await self.broadcast_to_waiting(self.waiting_queue, part_msg)

    async def send_log(self, result, player1_info, player2_info, rank):
        msg = {
            "type": "result",
            "player_A_id": player1_info.user_id,
            "player_B_id": player2_info.user_id,
            "score_A": result.player1_score,
            "score_B": result.player2_score,
            "rank": rank,
        }
        json_msg = json.dumps(msg)
        await self.system.send(json_msg)