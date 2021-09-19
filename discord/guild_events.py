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

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Union

from . import utils
from .asset import Asset
from .enums import GuildScheduledEventStatus, GuildScheduledEventType, try_enum
from .mixins import Hashable

if TYPE_CHECKING:
    from .abc import GuildChannel
    from .guild import Guild
    from .member import Member
    from .state import ConnectionState
    from .user import User

    from .types.guild_events import GuildScheduledEvent as GuildScheduledEventPayload
    from .types.guild_events import GuildScheduledEventEntityMeta

__all__ = ("GuildScheduledEvent", "GuildEventEntityMetadata")

MISSING: Any = utils.MISSING


# TODO: Still can be changed, fix later if possible
class GuildEventEntityMetadata(NamedTuple):
    speaker_ids: List[str]
    location: Optional[str]

    @classmethod
    def _from_data(cls, entity_data: GuildScheduledEventEntityMeta):
        return cls(
            speaker_ids=entity_data.get("speaker_ids", []),
            location=entity_data.get("location", None),
        )


class GuildScheduledEvent(Hashable):
    """Represents a Discord guild event.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: x == y

            Checks if two events are equal.

        .. describe:: x != y

            Checks if two events are not equal.

        .. describe:: hash(x)

            Returns the event's hash.

        .. describe:: str(x)

            Returns the event's name.

    Attributes
    ------------
    id: :class:`int`
        The event's ID.
    name: :class:`str`
        The event's name.
    description: Optional[:class:`str`]
        The event's description.
    start_time: :class:`datetime.datetime`
        The event's scheduled start time.
    end_time: Optional[:class:`datetime.datetime`]
        The event's scheduled end time.
    status: :class:`GuildScheduledEventStatus`
        The event's current status.
    guild: :class:`Guild`
        The guild the event belongs to.
    """

    __slots__ = (
        "_state",
        "id",
        "_type",
        "_members",
        "guild",
        "_channel",
        "name",
        "description",
        "_image",
        "status",
        "start_time",
        "end_time",
        "_entity_id",
        "_entity_metadata",
        "_member_count"
    )

    def __init__(
        self,
        *,
        state: ConnectionState,
        guild_or_channel: Union[Guild, GuildChannel],
        data: GuildScheduledEventPayload,
    ):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._type: int = data['entity_type']
        self._members: Dict[int, Member] = {}
        self._update(guild_or_channel, data)

    def __repr__(self) -> str:
        attrs = [
            ("id", self.id),
            ("name", self.name),
            ("guild", self.guild.name)
        ]
        joined = " ".join("%s=%r" % t for t in attrs)
        return f"<{self.__class__.__name__} {joined}>"

    def __str__(self) -> str:
        return self.name

    def _update(
        self,
        guild_or_channel: Union[Guild, GuildChannel],
        data: GuildScheduledEventPayload
    ):
        if isinstance(guild_or_channel, Guild):
            self.guild = guild_or_channel
            self._channel = None
        else:
            self._channel = guild_or_channel
            self.guild = guild_or_channel.guild

        self.name: str = data["name"]
        self.description: Optional[str] = data.get("description", None)
        self._image: Optional[str] = data.get("image", None)

        self.status: GuildScheduledEventStatus = try_enum(GuildScheduledEventStatus, data["status"])

        self.start_time: datetime = utils.parse_time(data["scheduled_start_time"])
        self.end_time = utils.parse_time(data.get("scheduled_end_time"))

        entity_id = data.get("entity_id", None)
        if entity_id:
            self._entity_id = int(entity_id)
        else:
            self._entity_id = None
        self._entity_metadata: GuildEventEntityMetadata = GuildEventEntityMetadata._from_data(
            data.get("entity_metadata", {})
        )
        self._member_count: Optional[int] = data.get("user_count")

    def _add_member(self, member: Member):
        self._members[member.id] = member

    def _remove_member(self, member: Member):
        self._members.pop(member.id, None)

    @property
    def type(self) -> GuildScheduledEventType:
        """:class:`GuildScheduledEventType`: The guild event Discord type."""
        return try_enum(GuildScheduledEventType, self._type)

    @property
    def channel(self) -> Optional[GuildChannel]:
        """Optional[:class:`abc.GuildChannel`]: The channel associated with this event,
        can be ``None``.
        """
        return self._channel

    @property
    def image(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: The image associated with the event, can be ``None``."""
        if not self._image:
            return None
        return Asset._from_guild_scheduled_event(
            self._state,
            self.id,
            self._image,
        )

    @property
    def members(self) -> List[Member]:
        """List[Union[:class:`Member`]]: List of user that subscribed to the event."""
        return list(self._members.values())

    @property
    def member_count(self) -> Optional[int]:
        """Optional[:class:`int`]: Total member that are subscribed to the event"""
        _counted = len(list(self._members.keys()))
        _from_data = getattr(self, "_member_count", None)
        return _counted if _from_data is None and _from_data > 0 else _from_data

    @property
    def speakers(self) -> List[Union[Member, User]]:
        """List[Union[:class:`Member`, :class:`User`]]: Return the list of speakers for the event"""
        speakers_ids = self._entity_metadata.speaker_ids
        all_speakers = []
        for speaker in speakers_ids:
            member = self.guild.get_member(int(speaker))
            if not member:
                member = self._state.get_user(int(speaker))
                if not member:
                    # TODO: Maybe better handling?
                    continue
            all_speakers.append(member)
        return all_speakers

    @property
    def location(self) -> Optional[str]:
        """Optional[:class:`str`]: Location of the event"""
        return self._entity_metadata.location

    @classmethod
    def from_gateway(cls, *, state: ConnectionState, data: GuildScheduledEventPayload) -> Optional[GuildScheduledEvent]:
        guild_id = int(data["guild_id"])
        guild: Optional[Guild] = state._get_guild(guild_id)
        if guild is None:
            return None

        try:
            channel = guild.get_channel(int(data["channel_id"]))
        except KeyError:
            channel = None
        else:
            guild = channel or guild

        return cls(state=state, guild_or_channel=guild, data=data)

    async def edit(
        self,
        *,
        name: str = MISSING,
        description: Optional[str] = MISSING,
        channel: Optional[GuildChannel] = MISSING,
        # TODO: Change this later
        privacy_level: Optional[Any] = MISSING,
        scheduled_start_time: Optional[datetime] = MISSING,
        entity_type: Optional[GuildScheduledEventType] = MISSING,
    ) -> GuildScheduledEvent:
        r"""|coro|

        Edits the guild event.

        You must have the :attr:`~Permissions.manage_events` permission
        to edit the guild event.

        Parameters
        -----------
        name: :class:`str`
            The new name of the event.
        description: Optional[:class:`str`]
            The new description of the event. Could be ``None`` for no description.
        channel: Optional[:class:`abc.GuildChannel`]
            The channel where the event will be conducted.
        privacy_level: Optional[Any]
            The event privacy level, same thing as StageInstance PrivacyLevel
        scheduled_start_time: Optional[:class:`datetime.datetime`]
            The new schedule start time, timezone must be UTC. If not it will be converted
            automatically.
        entity_type: Optional[:class:`GuildScheduledEventType`]
            The new ``entity type`` or ``type`` for the event.

        Raises
        -------
        Forbidden
            You do not have permissions to edit the guild event.
        HTTPException
            Editing the guild event failed.

        Returns
        --------
        :class:`GuildScheduledEvent`
            The newly updated guild event.
        """

        http = self._state.http

        fields: Dict[str, Any] = {}
        if name is not MISSING and entity_type is not None:
            fields["name"] = name

        if description is not MISSING:
            fields["description"] = description

        if channel is not MISSING:
            fields["channel_id"] = str(channel.id)

        if privacy_level is not MISSING and entity_type is not None:
            # TODO: Change later
            fields["privacy_level"] = privacy_level

        if scheduled_start_time is not MISSING and entity_type is not None:
            fields["scheduled_start_time"] = scheduled_start_time.replace(tzinfo=timezone.utc).isoformat()

        if entity_type is not MISSING and entity_type is not None:
            fields["entity_type"] = entity_type.value

        guild = self.guild

        data = await http.edit_guild_scheduled_event(self.id, **fields)
        try:
            channel = guild.get_channel(int(data["channel_id"]))
        except KeyError:
            channel = None
        else:
            guild = channel or guild
        return self.__class__(state=self._state, guild_or_channel=guild, data=data)

    async def delete(self) -> None:
        """|coro|

        Deletes the guild event.

        You must have the :attr:`~Permissions.manage_events` permission
        to be able to delete the guild event.

        Raises
        --------
        HTTPException
            Deleting the guild event failed.
        Forbidden
            You do not have permissions to delete the guild event.
        """

        await self._state.http.delete_guild_scheduled_event(self.id)
