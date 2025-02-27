import asyncio
import argparse
import websockets
from .IndividualGame import individual
from .TournamentGame import tournament


# ============================================
# 메인 서버: 모드에 따라 소켓 서버 및 매치메이커 실행
# ============================================
async def main_server(room_id, mode, port):
    if mode == "individual":
        # print(f"Starting individual match server on port {port}")
        # 매치메이커 태스크 시작
        game = await individual.create(room_id)
    elif mode == "tournament":
        # print(f"Starting tournament match server on port {port}")
        game = await tournament.create(room_id)
    else:
        print("Unknown mode")
        return
    asyncio.create_task(game.matchmaker())
    server = await websockets.serve(game.register, "0.0.0.0", port)
    await server.wait_closed()


def start_server(room_id, mode, port):
    asyncio.get_event_loop().run_until_complete(main_server(room_id, mode, port))
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--mode", choices=["individual", "tournament"], required=True,
    #                     help="게임 모드: 1:1 개인전 또는 4인 토너먼트")
    # parser.add_argument("--port", type=int, default=8765, help="서버 포트")
    # args = parser.parse_args()
    # asyncio.get_event_loop().run_until_complete(main_server(args.mode, args.port))
