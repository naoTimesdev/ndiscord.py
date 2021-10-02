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

from typing import List, Literal, Optional, TypedDict


class GuildScheduledEventUser(TypedDict):
    guild_scheduled_event_id: str
    user_id: str


# TODO: Still can be changed, fix later if possible
class GuildScheduledEventEntityMeta(TypedDict):
    speaker_ids: Optional[List[str]]
    location: Optional[str]


class _GuildScheduledEventOptional(TypedDict, total=False):
    channel_id: str
    description: str
    image: str
    scheduled_end_time: str
    entity_id: str
    user_count: int


GuildEventPrivacyLevel = Literal[1, 2]
GuildEventStatus = Literal[1, 2, 3, 4]
GuildEventEntityType = Literal[0, 1, 2, 3]


class GuildScheduledEvent(_GuildScheduledEventOptional):
    id: str
    guild_id: str
    name: str
    scheduled_start_time: str
    privacy_level: GuildEventPrivacyLevel
    status: GuildEventStatus
    entity_type: GuildEventEntityType
    entity_metadata: GuildScheduledEventEntityMeta
    sku_ids: List[str]
    # TODO: Change later when it's documented
    # TODO: This seems like something similar to Application SKUs
    skus: list
