import asyncio
import json
import random
import time
import argparse
import websockets
from abc import *

class IGame(metaclass=ABCMeta):
    def __init__(self):
        self.waiting_queue = []
        self.game_start = False

    @abstractmethod
    async def register(websocket, path):
        pass

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