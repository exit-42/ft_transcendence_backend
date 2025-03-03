import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from .roommanager import *
from asgiref.sync import sync_to_async

import logging

logger = logging.getLogger("django")


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """WebSocket 연결 시 실행"""
        await self.accept()

    async def disconnect(self, close_code):
        """WebSocket 연결 종료 시 실행"""
        pass  # 연결 해제 시 특별한 작업 없음

    async def receive(self, text_data):
        """WebSocket으로 JSON 메시지를 받을 때 실행"""
        try:
            data = json.loads(text_data)  # JSON 파싱
            message_type = data.get("type")
            if message_type == "ping":
                await self.send(json.dumps({"type": "pong", "message": "hello"}))
                return
            elif message_type == "join" or message_type == "exit":
                room_id = data.get("room_id")
                player = data.get("player")
                if not room_id or not player:
                    return

                if message_type == "join":
                    img_path, win_cnt, lose_cnt = room_manager.accept_room(
                        room_id, player
                    )
                    if img_path is None or win_cnt is None or lose_cnt is None:
                        await self.send(json.dumps({"type": "error"}))
                        logger.info("status : error " + text_data)
                    else:
                        await self.send(
                            json.dumps(
                                {
                                    "type": "success",
                                    "img_path": img_path,
                                    "winCnt": win_cnt,
                                    "loseCnt": lose_cnt,
                                }
                            )
                        )
                else:
                    success = room_manager.exit_room(room_id, player)
                    if not success:
                        logger.info("status : error " + text_data)
                        await self.send(json.dumps({"type": "error"}))
            elif message_type == "result":
                room_id = data.get("room_id")
                player_A_name = data.get("player_A_name")
                player_B_name = data.get("player_B_name")
                score_A = data.get("score_A")
                score_B = data.get("score_B")
                rank = data.get("rank")
                logger.info("cunsumer : setting result : " + str(room_id))
                if (
                    player_A_name is None
                    or player_B_name is None
                    or score_A is None
                    or score_B is None
                    or rank is None
                ):
                    await self.send(json.dumps({"type": "error"}))
                    logger.info("cunsumer : wrong argunemt")
                    return  # 에러 발생 시 함수 종료

                result = {
                    "player_A_name": player_A_name,
                    "player_B_name": player_B_name,
                    "score_A": score_A,
                    "score_B": score_B,
                    "rank": rank,
                }
                # room_manager.save_match(room_id, result)
                await sync_to_async(room_manager.save_match)(room_id, result)
            else:
                logger.info("status : error " + text_data)
                await self.send(json.dumps({"type": "error"}))

        except json.JSONDecodeError:
            logger.info("status : error " + text_data)
            await self.send(json.dumps({"type": "error"}))
