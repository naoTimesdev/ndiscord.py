"""
The MIT License (MIT)

Copyright (c) 2021-present naoTimesdev

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from aiohttp import web
import aiohttp
from .api import api_route

API_VERSION = "v9"


async def discord_gateway_mock(request):
    ws = web.WebSocketResponse(timeout=30.0)
    print("Initiating websocket request from", request)
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            # Parse information.
            pass
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print("ws connection closed with exception %s" %
                  ws.exception())

    print("Websocket connection closed", request)
    return ws


def create_app():
    app = web.Application()

    app.add_subapp(f"/api/{API_VERSION}/", api_route)
    app.add_routes([web.get("/mockgateway", discord_gateway_mock)])
    return app
