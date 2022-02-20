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

from __future__ import annotations

from typing import Dict, List, Literal, Optional, TypedDict

from .snowflake import Snowflake


class _DiscoveryCategoryNameOptional(TypedDict, total=False):
    localizations: Dict[str, str]


class DiscoveryCategoryName(_DiscoveryCategoryNameOptional):
    default: str


class DiscoveryCategory(TypedDict):
    id: int
    name: DiscoveryCategoryName
    is_primary: bool


class DiscoverySearchTermValidation(TypedDict):
    valid: bool


# https://gist.github.com/noaione/61de9670d2e43193ded8984102fa1231
# Last updated: 2021-09-26 10:25:00 GMT+8
DiscoveryCategoryType = Literal[
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
]


class DiscoverySubcategory(TypedDict):
    guild_id: Snowflake
    category_id: DiscoveryCategoryType


class DiscoveryMetadata(TypedDict):
    guild_id: Snowflake
    primary_category_id: DiscoveryCategoryType
    keywords: Optional[List[str]]
    emoji_discoverability_enabled: bool
    partner_actioned_timestamp: Optional[str]
    partner_application_timestamp: Optional[str]
    category_ids: List[DiscoveryCategoryType]
