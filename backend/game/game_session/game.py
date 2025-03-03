import asyncio
import ssl
import websockets
import os
from .IndividualGame import individual
from .TournamentGame import tournament


# ============================================
# 메인 서버: 모드에 따라 소켓 서버 및 매치메이커 실행 (wss 지원)
# ============================================
async def main_server(room_id, mode, port, certfile, keyfile):
    if mode == "individual":
        game = await individual.create(room_id)
    elif mode == "tournament":
        game = await tournament.create(room_id)
    else:
        print("Unknown mode")
        return

    asyncio.create_task(game.matchmaker())

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    # wss 서버 실행
    server = await websockets.serve(game.register, "0.0.0.0", port, ssl=ssl_context)
    await server.wait_closed()


def start_server(
    room_id,
    mode,
    port,
    certfile=os.environ.get("WSS_CERT_PATH"),
    keyfile=os.environ.get("WSS_PRIVATE_KEY_PATH"),
):
    asyncio.get_event_loop().run_until_complete(
        main_server(room_id, mode, port, certfile, keyfile)
    )
