"""

"""
from typing import ClassVar

import discord.http

__all__ = ("monkeypatch_route",)


def monkeypatch_route():
    OriginalRoute = discord.http.Route

    class PatchedRoute(OriginalRoute):
        BASE: ClassVar[str] = "http://127.0.0.1:7200/api/v9"

    discord.http.Route = PatchedRoute
