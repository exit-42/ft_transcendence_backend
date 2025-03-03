import multiprocessing
import socket
import random
from log.utils import *

from .game_session.game import *
import os

import logging

logger = logging.getLogger("django")


class RoomManager:
    def __init__(self):
        self.rooms = {}  # 현재 존재하는 방 정보
        self.next_room_id = 1  # 새로운 방 ID를 위한 카운터
        self.available_room_ids = []  # 삭제된 방 ID 재사용을 위한 리스트

        # 사용 가능한 포트 리스트
        self.used_ports = set()
        low = int(os.environ.get("PORT_START"))
        high = int(os.environ.get("PORT_END"))
        self.candidate_ports = list(range(low, high + 1))
        random.shuffle(self.candidate_ports)

    def get_open_port(self):
        temporary_not_avail = []
        while self.candidate_ports:
            port = self.candidate_ports.pop()
            if port in self.used_ports:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                    s.listen(1)
                    self.used_ports.add(port)
                    return port
                except OSError as e:
                    temporary_not_avail.append(port)
                    continue
        # 후보 리스트가 소진되면 예외를 발생시킵니다.
        self.candidate_ports.extend(temporary_not_avail)
        logger.debug("room manager : no port available")
        return None

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
            - 성공 : room_id, port
            - 실패 : None
        """
        room_id = self.generate_room_id()
        game_id = create_game(mode)
        port = self.get_open_port()
        if port is None:
            return None
        process = multiprocessing.Process(
            target=start_server, args=(room_id, mode, port)
        )
        process.start()
        pid = process.pid

        self.rooms[room_id] = {
            "player_number": 0,
            "room_id": room_id,
            "game_id": game_id,
            "room_manager": "",
            "socket_port_number": port,
            "players": {},
            "candidate": {},
            "pid": pid,
            "mode": mode,
            "start": False,
        }
        return room_id, port

    def delete_room(self, room_id):
        """
        @brief 해당 방을 삭제하는 함수

        @param room_id, user

        @return
            - 성공 : True
            - 에러 : False
        """
        room = self.rooms.pop(room_id, None)
        if room:
            process = room.get("process")
            if process and process.is_alive():
                process.terminate()
            self.available_room_ids.append(room_id)  # 삭제된 ID 재사용 가능하도록 추가
            self.available_room_ids.sort()  # 작은 ID부터 우선 재사용
            if room["socket_port_number"] is not None:
                self.candidate_ports.append(room["socket_port_number"])
            return True
        logger.debug("room manager : wrong room_id (" + str(room_id) + ")")
        return False

    def join_room(self, room_id, user):
        """
        @brief 해당 방에 입장을 신청하는 함수

        @param room_id, user

        @return
            - 성공 : room 객체
            - 에러 : None

        @detail 해당 유저를 추후 accpet_room에서 사용할 후보군에 추가
                반드시 accept_room이 호출되기 전 join_room이 호출 되어야 함
        """
        room = self.rooms.get(int(room_id))
        if room:
            if room["start"] is True:
                return None
            if user.nickname not in room["candidate"]:
                room["candidate"][user.nickname] = user
            return room
        logger.debug("room manager : wrong room_id (" + str(room_id) + ")")
        return None

    def accept_room(self, room_id, player_name):
        """
        @brief 해당 방에 최종적으로 입장 허용하는 함수

        @param room_id, player_name

        @return
            - 성공 : imagePath, winCnt, loseCnt
            - 에러 : None

        @detail 해당 room에서 후보에 있는 유저라면 플레이어로 추가
                방이 비어있었다면 해당 유저를 방장으로 할당
                후보에 없는 유저라면 추가하지 않고 None 반환
        """
        room = self.rooms.get(room_id)
        if room and player_name in room["candidate"]:
            user = room["candidate"][player_name]
            room["players"][player_name] = user
            del room["candidate"][player_name]
            # 방장 할당
            if (room["player_number"]) == 0:
                room["room_manager"] = player_name
            # 방 정원 확인
            if room["mode"] == "tournament":
                if len(room["players"]) == 4:
                    room["start"] = True
            elif room["mode"] == "individual":
                if len(room["players"]) == 2:
                    room["start"] = True
            room["player_number"] += 1
            return user.imagePath, user.winCnt, user.loseCnt
        logger.debug(
            "room manager : wrong user " + player_name + " in " + str(room_id) + ""
        )
        return None

    def exit_room(self, room_id, player_name):
        """
        @brief 방에서 퇴장하는 함수

        @param room_id, player_name

        @return
            - 성공 : True
            - 에러 발생 : False

        @detail 해당 room_id를 가진 방에서 플레이어를 제거
                해당 플레이어가 방장이라면 남아있는 플레이어 중 한명을 방장으로 할당
                만약 마지막으로 남아있던 플레이어라면 해당 방을 제거
        """
        room = self.rooms.get(int(room_id))
        if room:
            if player_name in room["players"]:
                del room["players"][player_name]
            if player_name in room["candidate"]:
                del room["candidate"][player_name]
            room["player_number"] -= 1

            # 방장이 나가면 다른 플레이어를 방장으로 설정
            if room["room_manager"] == player_name:
                if len(list(room["players"])) > 0:
                    room["room_manager"] = list(room["players"])[0]
                else:
                    return self.delete_room(room_id)  # 마지막 플레이어라면 방 삭제
            return True
        logger.debug("room manager : wrong room_id (" + str(room_id) + ")")
        return False

    def save_match(self, room_id, result):
        """
        @brief match에 대한 로그 추가

        @param room_id, player_name

        @return
            - 성공 : True
            - 에러 발생 : False

        @detail 해당 room_id를 가진 방에 대한 로그 추가 및 모든 match가 끝난다면 게임 종료로 상태 변환
                만약 tournament인 경우 rank가 2인 경우(결승전이 종료한 경우)만 게임 종료로 변환
                그 외 match 저장 후 게임 종료로 변환
        """
        room = self.rooms.get(room_id)
        result["player_A_id"] = room["players"][result["player_A_name"]].id
        result["player_B_id"] = room["players"][result["player_B_name"]].id
        result["game_id"] = room["game_id"]
        if create_match_log(result) is not True:
            return False
        if room["mode"] == "tournament":
            if result["rank"] == 2:
                set_game_end(room["game_id"])
                self.delete_room(room_id)
        else:
            set_game_end(room["game_id"])
            self.delete_room(room_id)
        return True


# 전역 인스턴스로 사용 (여러 consumer에서 공유 가능)
room_manager = RoomManager()
