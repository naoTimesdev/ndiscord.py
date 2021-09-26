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

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from .enums import DiscoveryCategoryType, try_enum
from .errors import InvalidArgument, InvalidData
from .mixins import EqualityComparable
from .utils import find, parse_time

if TYPE_CHECKING:
    from .guild import Guild
    from .state import ConnectionState
    from .types.discovery import DiscoveryCategory as DiscoveryCategoryPayload
    from .types.discovery import DiscoveryMetadata as DiscoveryMetadataPayload


__all__ = ("DiscoveryCategory", "DiscoveryMetadata")


class DiscoveryCategory(EqualityComparable):
    """Represents a discovery category.

    .. container:: operations

        .. describe:: x == y

            Checks if two category are the same.

        .. describe:: x != y

            Checks if two category are not the same.

        .. describe:: str(x)

            Returns the default name for the category.

    Attributes
    ----------
    id: :class:`int`
        The ID of the category.
    name: :class:`str`
        The default name of the category in English.
    primary: :class:`bool`
        Whether the category can be set as a guild's primary category.
    localizations: Dict[:class:`str`, :class:`str`]
        The name of the category in every language supported by Discord.
    """

    __slots__: Tuple[str, ...] = (
        "id",
        "name",
        "primary",
        "localizations",
    )

    def __init__(self, *, data: DiscoveryCategoryPayload):
        self.id: int = data["id"]
        names = data["name"]
        self.name: str = names["default"]
        self.primary: bool = data["is_primary"]
        self.localizations: Dict[str, str] = names.get("localizations", {})

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<DiscoveryCategory id={self.id} name={self.name}>"


class DiscoveryMetadata:
    """Represents a discovery metadata for a guild.

    Attributes
    -----------
    TBW
    """

    __slots__ = (
        "guild",
        "primary_category_type",
        "keywords",
        "emoji_discoverability",
        "subcategories_type",
        "partner_actioned_timestamp",
        "partner_application_timestamp",
        "_state",
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: DiscoveryMetadataPayload):
        self._state: ConnectionState = state

        self.guild: Guild = guild
        self._update(data)

    def _update(self, data: DiscoveryMetadataPayload):
        self.primary_category_type: DiscoveryCategoryType = try_enum(DiscoveryCategoryType, data["primary_category_id"])
        self.keywords: List[str] = data.get("keywords", []) or []
        self.emoji_discoverability: bool = data["emoji_discoverability_enabled"]
        self.subcategories_type: List[DiscoveryCategoryType] = [
            try_enum(DiscoveryCategoryType, x) for x in data.get("subcategories", [])
        ]

        self.partner_actioned_timestamp: Optional[datetime] = parse_time(data.get("partner_actioned_timestamp"))
        self.partner_application_timestamp: Optional[datetime] = parse_time(data.get("partner_application_timestamp"))

    async def edit(
        self,
        *,
        primary_category: Union[DiscoveryCategory, DiscoveryCategoryType] = DiscoveryCategoryType.general,
        keywords: List[str] = [],
        emoji_discoverability: Optional[bool] = None,
    ) -> None:
        """Edits the discovery metadata of the guild.

        Parameters
        -----------
        primary_category: Union[:class:`.DiscoveryCategory`, :class:`DiscoveryCategoryType`]
            The primary category of the guild, can be the enums or the class.
        keywords: List[:class:`str`]
            A list of keywords to be used for searching. Maximum of 10.
        emoji_discoverability: :class:`bool`
            Whether to enable emoji discoverability.

        Raises
        -------
        Forbidden
            You do not have permissions to edit the guild.
        HTTPException
            Editing the guild failed.
        """

        fields: Dict[str, Any] = {}
        if isinstance(primary_category, DiscoveryCategory):
            fields["primary_category_id"] = primary_category.id
        elif isinstance(primary_category, DiscoveryCategoryType):
            fields["primary_category_id"] = primary_category.value

        if keywords:
            fields["keywords"] = keywords
        else:
            fields["keywords"] = self.keywords

        if emoji_discoverability is not None:
            fields["emoji_discoverability_enabled"] = emoji_discoverability
        else:
            fields["emoji_discoverability_enabled"] = self.emoji_discoverability

        data = await self._state.http.edit_guild_discovery_metadata(self.guild.id, fields=fields)
        self._update(data)

    async def primary_category(self) -> DiscoveryCategory:
        """Retrieves the primary category of the guild.

        Raises
        -------
        InvalidData
            The category ID could not be recognised.
        HTTPException
            Fetching the primary category failed.

        Returns
        -------
        :class:`.DiscoveryCategory`
            The primary category of the guild.
        """
        categories = await self._state.http.get_discovery_categories()

        category = find(lambda x: x["id"] == self.primary_category_type.value, categories)
        if category is None:
            raise InvalidData(f"Unknown primary category ID {self.primary_category_type.value}.")
        return DiscoveryCategory(data=category)

    async def subcategories(self) -> List[DiscoveryCategory]:
        """|coro|

        Retrieves the subcategories of the guild discovery.

        Raises
        -------
        HTTPException
            Fetching the subcategories failed.

        Returns
        -------
        List[:class:`.DiscoveryCategory`]
            The subcategories of the guild.
        """
        if len(self.subcategories_type) < 1:
            return []
        categories = await self._state.http.get_discovery_categories()

        subcategories = filter(
            lambda x: try_enum(DiscoveryCategoryType, x["id"]) in self.subcategories_type, categories
        )
        return [DiscoveryCategory(data=category) for category in subcategories]

    async def add_subcategory(self, category: Union[DiscoveryCategory, DiscoveryCategoryType]) -> None:
        """|coro|

        Add a discovery subcategory to the guild discovery.

        You must have the :attr:`~Permissions.manage_guild` permission to
        do this.

        Raises
        -------
        InvalidArgument
            The category is not a valid subcategory.
        Forbidden
            You do not have permission to add the subcategory.
        HTTPException
            Adding the subcategory failed.
        """
        subcategory_id = category.id if isinstance(category, DiscoveryCategory) else category.value
        if not isinstance(subcategory_id):
            raise InvalidArgument(f"Invalid category ID {subcategory_id}.")
        subcategory = await self._state.http.add_guild_discovery_subcategory(self.guild.id, subcategory_id)
        self.subcategories_type.append(try_enum(DiscoveryCategoryType, subcategory["category_id"]))

    async def remove_subcategory(self, category: Union[DiscoveryCategory, DiscoveryCategoryType]) -> None:
        """|coro|

        Remove a discovery subcategory from the guild discovery.

        You must have the :attr:`~Permissions.manage_guild` permission to
        do this.

        Raises
        -------
        InvalidArgument
            The category is not a valid subcategory.
        Forbidden
            You do not have permission to remove the subcategory.
        HTTPException
            Removing the subcategory failed.
        """
        subcategory_id = category.id if isinstance(category, DiscoveryCategory) else category.value
        if not isinstance(subcategory_id):
            raise InvalidArgument(f"Invalid category ID {subcategory_id}.")
        await self._state.http.remove_guild_discovory_subcategory(self.guild.id, subcategory_id)
        try:
            self.subcategories_type.remove(try_enum(DiscoveryCategoryType, subcategory_id))
        except Exception:
            pass
