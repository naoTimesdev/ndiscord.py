from aiohttp import web
from ._utils import SNOWFLAKE_MOCK
from .middleware import authorization_middleware, post_json_middleware

routes = web.RouteTableDef()
open_routes = web.RouteTableDef()

users_api = web.Application(middlewares=[authorization_middleware, post_json_middleware])


user_base_dict = {
    "id": SNOWFLAKE_MOCK,
    "username": "Mock",
    "discriminator": "1234",
}


@routes.get("/@me")
async def static_login_api(request: web.Request) -> web.Response:
    json_response = {
        "bot": True,
        "system": False,
        "mfa_enabled": False,
        "verified": True,
    }
    json_response.update(user_base_dict)
    return web.json_response(json_response)


@routes.patch("/@me")
async def edit_profile_api(request: web.Request) -> web.Response:
    try:
        json_contents = await request.json()
    except ValueError:
        json_contents = {}

    username = json_contents.get("username", None)
    js_resp = {
        "bot": True,
        "system": False,
        "mfa_enabled": False,
        "verified": True,
    }
    js_resp.update(user_base_dict)
    if username is not None:
        js_resp["username"] = username
    return web.json_response(js_resp)


@routes.post("/@me/channels")
async def start_private_message_api(request: web.Request) -> web.Response:
    json_contents = await request.json()
    if "recipient_id" not in json_contents:
        return web.json_response({"code": 0, "message": "Missing recipient_id data in JSON"}, status=400)
    recipient_id = json_contents["recipient_id"]
    json_response = {
        "id": SNOWFLAKE_MOCK,
        "type": 1,
        "recipients": [
            {
                "id": recipient_id,
                "username": "Mock",
                "discriminator": "1234",
            }
        ],
    }
    return web.json_response(json_response)


@routes.post("/{user_id:\d+}/channels")  # noqa
async def start_group_api(request: web.Request) -> web.Response:
    json_contents = await request.json()
    user_id_match = request.match_info["user_id"]
    if "recipients" not in json_contents:
        return web.json_response({"code": 0, "message": "Missing recipients data in JSON"}, status=400)
    recipients = json_contents["recipients"]
    if not isinstance(recipients, list):
        return web.json_response({"code": 0, "message": "recipients is not a list"}, status=400)
    json_response = {
        "id": SNOWFLAKE_MOCK,
        "name": "Mock",
        "type": 3,
        "recipients": [],
        "owner_id": user_id_match,
    }
    for recipient in recipients:
        json_response["recipients"].append(
            {
                "id": recipient,
                "username": "Mock",
                "discriminator": "1234",
            }
        )
    return web.json_response(json_response)


users_api.add_routes(routes)
