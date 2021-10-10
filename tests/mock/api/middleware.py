from aiohttp import web


@web.middleware
async def authorization_middleware(request: web.Request, handler: web.RequestHandler):
    if not request.headers.get("Authorization", "").startswith("Bot "):
        return web.json_response(
            {"code": 50014, "message": "Invalid authentication token"},
            status=401,
        )
    return await handler(request)


@web.middleware
async def post_json_middleware(request: web.Request, handler: web.RequestHandler):
    if request.method != "POST":
        return await handler(request)
    if "application/json" not in request.content_type:
        return web.json_response(
            {"code": 0, "message": "Missing JSON data"},
            status=400,
        )
    return await handler(request)
