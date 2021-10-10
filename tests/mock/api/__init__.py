"""
tests.mock.api
~~~~~~~~~~~~~~~

A collection of API routes for mocking HTTP request/response.

:copyright: (c) 2021-present naoTimesdev
:license: MIT, see LICENSE for more details.
"""

# flake8: noqa

from aiohttp import web

from .users import users_api

api_route = web.Application()
api_route.add_subapp("/users/", users_api)
