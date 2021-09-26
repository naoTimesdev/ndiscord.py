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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from . import utils
from .errors import InvalidArgument
from .partial_emoji import _EmojiTag

if TYPE_CHECKING:
    from .abc import Snowflake
    from .emoji import Emoji
    from .guild import Guild
    from .partial_emoji import PartialEmoji
    from .types.welcome_screen import WelcomeScreen as WelcomeScreenPayload
    from .types.welcome_screen import WelcomeScreenChannel as WelcomeScreenChannelPayload

__all__ = (
    "WelcomeChannel",
    "WelcomeScreen",
)

MISSING: Any = utils.MISSING


class WelcomeChannel:
    """Represents a :class:`.WelcomeScreen` welcome channel.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: str(x)

            Returns the description of the welcome channel.

    Attributes
    -----------
    channel: :class:`abc.Snowflake`
        The snowflake of the channel, this can be any channel.
    description: :class:`str`
        The description of the welcome channel.
    emoji: Optional[Union[:class:`Emoji`, :class:`PartialEmoji`, :class:`str`]]
        The emoji of the welcome channel if exists.
    """

    __slots__ = ("channel", "description", "emoji")

    def __init__(self, *, channel: Snowflake, description: str, emoji: Union[PartialEmoji, Emoji, str] = None):
        self.channel: Snowflake = channel
        self.description: str = description
        self.emoji: Union[Emoji, PartialEmoji, str] = emoji

    def __repr__(self) -> str:
        return f"<WelcomeChannel channel={self.channel!r} description={self.description!r} emoji={self.emoji!r}>"

    def __str__(self) -> str:
        return self.description

    @classmethod
    def _from_dict(cls: Type[WelcomeChannel], *, data: WelcomeScreenChannelPayload, guild: Guild) -> WelcomeChannel:
        channel_id = utils._get_as_snowflake(data, "channel_id")
        channel = guild.get_channel(channel_id)
        description = data.get("description")
        _emoji_id = utils._get_as_snowflake(data, "emoji_id")
        _emoji_name = data["emoji_name"]

        if _emoji_id:
            # Custom emoji
            emoji = utils.get(guild.emojis, id=_emoji_id)
        else:
            emoji = _emoji_name

        return cls(channel=channel, description=description, emoji=emoji)

    def to_dict(self) -> WelcomeScreenChannelPayload:
        res: WelcomeScreenChannelPayload = {
            "channel_id": self.channel.id,
            "description": self.description,
            "emoji_id": None,
            "emoji_name": None,
        }

        if isinstance(self.emoji, _EmojiTag):
            res["emoji_id"] = self.emoji.id
            res["emoji_name"] = self.emoji.name
        else:
            res["emoji_name"] = str(self.emoji)

        return res


class WelcomeScreen:
    """Represents a welcome screen for a :class:`Guild`.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: str(x)

            Returns the description of the welcome channel.

    Attributes
    -----------
    guild: :class:`Guild`
        The guild the welcome screen belongs to.
    description: Optional[:class:`str`]
        The description of the welcome screen.
    channels: List[:class:`WelcomeChannel`]
        The list of welcome channels.
    """

    __slots__ = (
        "guild",
        "description",
        "channels",
        "_state",
    )

    def __init__(self, *, guild: Guild, data: WelcomeScreenPayload):
        self.guild: Guild = guild
        self._state = guild._state

        self._update(data)

    def _update(self, data: WelcomeScreenPayload):
        self.description: Optional[str] = data.get("description")
        welcome_channels = data.get("welcome_channels", [])

        self.channels: List[WelcomeChannel] = [
            WelcomeChannel._from_dict(data=channel, guild=self.guild) for channel in welcome_channels
        ]

    def __repr__(self) -> str:
        return f"<WelcomeScreen guild={self.guild.id} description={self.description!r}>"

    def __str__(self) -> str:
        return self.description

    @property
    def enabled(self) -> bool:
        """bool: Returns if the welcome screen is enabled."""
        return "WELCOME_SCREEN_ENABLED" in self.guild.features

    async def edit(
        self,
        *,
        enabled: bool = MISSING,
        channels: List[WelcomeChannel] = MISSING,
        description: str = MISSING,
        reason: str = None,
    ) -> None:
        """|coro|

        Edit the welcome screen of a guild.

        You must have the :attr:`~Permissions.manage_guild` permission in the
        guild to do this.

        .. note::
            Welcome channels can only accept custom emojis if :attr:`~Guild.premium_tier` is level 2 or above.

        Parameters
        -----------
        enabled: :class:`bool`
            Should we enable the welcome screen of not.
        channels: List[:class:`.WelcomeChannel`]
            The channels to use for the welcome screen.
        description: :class:`str`
            The description of the welcome screen.
        reason: Optional[:class:`str`]
            The reason for editing the welcome screen. Shows up on the audit log.


        Raises
        -------
        InvalidArgument
            If the welcome channels are not valid.
        Forbidden
            Not allowed to edit the welcome screen.
        HTTPException
            Editing the welcome screen failed.
        """

        fields: Dict[str, Any] = {}

        if enabled is not MISSING:
            fields["enabled"] = enabled
        else:
            fields["enabled"] = self.enabled

        if channels is not MISSING:
            welcome_channels = []
            for channel in channels:
                if not isinstance(channel, WelcomeChannel):
                    raise InvalidArgument("channels must be of type WelcomeChannel")
                welcome_channels.append(channel.to_dict())
            fields["welcome_channels"] = welcome_channels

        if description is not MISSING:
            fields["description"] = description

        if fields:
            data = await self._state.http.edit_welcome_screen(self.guild.id, reason=reason, **fields)
            self._update(data)
