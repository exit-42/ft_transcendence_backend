import json
import asyncio
import uuid
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    ball_position = {"x": 50, "y": 50, "vx": 2, "vy": 0}  # 공의 초기 위치 
    game_group_name = "game_group"
    players = {}

    update_lock = asyncio.Lock()

    async def connect(self):
        self.player_id = str(uuid.uuid4())
        await self.accept()

        await self.channel_layer.group_add(
            self.game_group_name, self.channel_name
        )

        await self.send(
            text_data=json.dumps({"type": "playerId", "playerId": self.player_id})
        )

        async with self.update_lock:
            self.players[self.player_id] = {
                "id": self.player_id,
                "x": 500,
                "y": 500,
                "facing": 0,
                "dx": 0,
                "dy": 0,
                "thrusting": False,
            }
 
        if len(self.players) == 1:
            asyncio.create_task(self.game_loop())

    async def disconnect(self, close_code):
        async with self.update_lock:
            if self.player_id in self.players:
                del self.players[self.player_id]

        await self.channel_layer.group_discard(
            self.game_group_name, self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        input_type = text_data_json.get("key", "")
        async with self.update_lock:
            if input_type == "ArrowLeft":
                self.ball_position["x"] -= 1
            elif input_type == "ArrowRight":
                self.ball_position["x"] += 1
            elif input_type == "ArrowUp":
                self.ball_position["y"] -= 1
            elif input_type == "ArrowDown":
                self.ball_position["y"] += 1

    async def state_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "state_update",
                    "objects": event["objects"],
                }
            )
        )

    async def game_loop(self):
        while len(self.players) > 0:
            await self.channel_layer.group_send(
                self.game_group_name,
                {"type": "state_update", "objects": self.ball_position},
            )
            await asyncio.sleep(0.05)