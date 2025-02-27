import multiprocessing
import socket
import random
from log.utils import *
from .game_session.game import *
import os

import logging

logger = logging.getLogger('django')

class RoomManager:
    def __init__(self):
        self.rooms = {}  # 현재 존재하는 방 정보
        self.next_room_id = 1  # 새로운 방 ID를 위한 카운터
        self.available_room_ids = []  # 삭제된 방 ID 재사용을 위한 리스트

    def get_open_port(self):
        low = os.environ.get("PORT_START")
        high = os.environ.get("PORT_END")
        while True:
            port = random.randint(int(low), int(high))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    s.listen(1)
                    port = s.getsockname()[1]
                    s.close()
                    return port
                except OSError:
                    continue

    def generate_room_id(self):
        if self.available_room_ids:
            return self.available_room_ids.pop(0)  # 삭제된 ID 중 가장 작은 값 사용
        room_id = self.next_room_id
        self.next_room_id += 1
        return room_id

    def create_room(self, mode):
        """
        @brief 새로운 방을 생성하는 함수

        @param mode

        @return
            - room_id, port
        """
        room_id = self.generate_room_id()
        game_id = create_game(mode)
        port = self.get_open_port()
        process = multiprocessing.Process(target=start_server, args=(room_id, mode, port))
        process.start()
        pid = process.pid

        self.rooms[room_id] = {
            "player_number": 0,  # 방장은 바로 입장
            "room_id": room_id,
            "game_id": game_id,
            "room_manager": "",  # 방장은 첫 입장한 사람
            "socket_port_number": port,
            "players": {},
            "candidate": {},
            "pid": pid,
            "mode": mode,
        }
        return room_id, port

    def delete_room(self, room_id):
        room = self.rooms.pop(room_id, None)
        if room:
            process = room.get("process")
            if process and process.is_alive():
                process.terminate()
            self.available_room_ids.append(room_id)  # 삭제된 ID 재사용 가능하도록 추가
            self.available_room_ids.sort()  # 작은 ID부터 우선 재사용
            return True
        return False

    def join_room(self, room_id, user):
        room = self.rooms.get(room_id)
        if room and user.nickname not in room["candidate"]:
            room["candidate"][user.nickname] = user.id
            return True
        return False
    
    def accept_room(self, room_id, player_name):
        room = self.rooms.get(room_id)
        logger.info(room["candidate"])
        if room and player_name in room["candidate"]:
            room["players"][player_name] = room["candidate"][player_name]
            del room["candidate"][player_name]
            if (room["player_number"]) == 0:
                room["room_manager"] = player_name
            room["player_number"] += 1
            logger.info("accepted : " + player_name)
            return True
        return False

    def exit_room(self, room_id, player_name):
        """
        @brief 방에서 퇴장하는 함수

        @param room_id, player_name

        @return
            - room 에 대한 정보 객체
        """
        room = self.rooms.get(room_id)
        if room:
            if player_name in room["players"]:
                room["players"].remove(player_name)
            if player_name in room["candidate"]:
                room["candidate"].remove(player_name)
            room["player_number"] -= 1

            # 방장이 나가면 다른 플레이어를 방장으로 설정
            if room["room_manager"] == player_name:
                if list(room["players"])[0]:
                    room["room_manager"] = list(room["players"])[0]
                else:
                    return self.deleteRoom(room_id)  # 마지막 플레이어라면 방 삭제

            return room
        return None

    def save_match(self, room_id, result):
        """
        @brief match에 대한 로그 추가

        @param room_id, player_name

        @return
            - room_id

        @detail 해당 room_id를 가진 방에 대한 로그 추가 및 모든 match가 끝난다면 종료로 상태 변환
        """
        room = self.rooms.get(room_id)
        result["user_A_id"] = room["room_id"]["players"][result["user_A_name"]]
        result["user_B_id"] = room["room_id"]["players"][result["user_B_name"]]
        result["gamd_id"] = room["game_id"]
        create_match_log(result)
        if room["mode"] == "tournament":
            if result["rank"] == 2:
                set_game_end(room["game_id"])
                self.delete_room(room_id)
        else:
            set_game_end(room["game_id"])
            self.delete_room(room_id)


# 전역 인스턴스로 사용 (여러 consumer에서 공유 가능)
room_manager = RoomManager()
