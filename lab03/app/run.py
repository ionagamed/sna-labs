import datetime
import json

from aiohttp import web, WSMsgType
from loguru import logger


async def get_main_page(request):
    logger.info("GET main page received")
    with open("./main_page.html") as f:
        return web.Response(body=f.read(), content_type="text/html")


async def get_current_time_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    logger.info("New WebSocket connection")

    async for message in ws:
        if message.type == WSMsgType.TEXT:
            payload = json.loads(message.data)
            if payload["action"] == "close":
                await ws.close()
            else:
                now = datetime.datetime.now().timestamp()
                logger.info("Sending timestamp to a WebSocket client")
                await ws.send_str(json.dumps({"now": now}))
        elif message.type == WSMsgType.ERROR:
            logger.error(f"WebSocket closed with {ws.exception()}")

    logger.info("WebSocket connection closed")

    return ws


def main():
    app = web.Application()

    app.add_routes([
        web.get("/", get_main_page),
        web.get("/ws", get_current_time_ws)
    ])

    web.run_app(app, host="localhost", port=9000)


if __name__ == '__main__':
    main()
