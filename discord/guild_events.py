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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from . import utils
from .abc import GuildChannel
from .asset import Asset
from .enums import GuildScheduledEventPrivacyLevel, GuildScheduledEventStatus, GuildScheduledEventType, try_enum
from .mixins import Hashable

if TYPE_CHECKING:
    from .guild import Guild
    from .member import Member
    from .state import ConnectionState
    from .types.guild_events import GuildScheduledEvent as GuildScheduledEventPayload
    from .types.guild_events import GuildScheduledEventEntityMeta
    from .user import User

__all__ = ("GuildScheduledEvent", "GuildEventEntityMetadata")

MISSING: Any = utils.MISSING


class GuildEventEntityMetadata:
    """
    Represents metadata about a guild event.

    Attributes
    ----------
    speaker_ids: List[:class:`int`]
        A list of user IDs that are allowed to speak in the stage channel.
        This will be filled if the event type is a :attr:`GuildScheduledEventType.stage_instance` event.
    location: Optional[:class:`str`]
        The location of the event, this will be filled if the event type
        is :attr:`GuildScheduledEventType.location` event.
    """

    __slots__ = ("location", "speaker_ids")

    def __init__(self, *, data: GuildScheduledEventEntityMeta):
        speaker_ids = data.get("speaker_ids", [])
        self.location: Optional[str] = data.get("location")
        self.speaker_ids = list(map(int, speaker_ids))


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
    type: :class:`GuildScheduledEventType`
        The guild event type.
    start_time: :class:`datetime.datetime`
        The event's scheduled start time.
    end_time: Optional[:class:`datetime.datetime`]
        The event's scheduled end time.
    status: :class:`GuildScheduledEventStatus`
        The event's current status.
    privacy_level: :class:`GuildScheduledEventPrivacyLevel`
        The event's privacy level.
    guild: :class:`Guild`
        The guild the event belongs to.
    """

    __slots__ = (
        "_state",
        "id",
        "type",
        "_members",
        "guild",
        "_channel",
        "name",
        "description",
        "_image",
        "status",
        "privacy_level",
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
        if isinstance(guild_or_channel, GuildChannel):
            self.guild = guild_or_channel
            self._channel = guild_or_channel.guild
        else:
            self._channel = None
            self.guild = guild_or_channel

        self.name: str = data["name"]
        self.description: Optional[str] = data.get("description", None)
        self._image: Optional[str] = data.get("image", None)

        self.status: GuildScheduledEventStatus = try_enum(GuildScheduledEventStatus, data["status"])
        self.privacy_level: GuildScheduledEventPrivacyLevel = try_enum(
            GuildScheduledEventPrivacyLevel, data["privacy_level"]
        )
        self.type = try_enum(GuildScheduledEventType, data.get("entity_type", 0))

        self.start_time: datetime = utils.parse_time(data["scheduled_start_time"])
        self.end_time = utils.parse_time(data.get("scheduled_end_time"))

        entity_id = data.get("entity_id", None)
        if entity_id:
            self._entity_id = int(entity_id)
        else:
            self._entity_id = None
        self._entity_metadata: GuildEventEntityMetadata = GuildEventEntityMetadata(
            data=data.get("entity_metadata", {})
        )
        self._member_count: Optional[int] = data.get("user_count")

    def _add_member(self, member: Member):
        self._members[member.id] = member

    def _remove_member(self, member: Member):
        self._members.pop(member.id, None)

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

    def get_member(self, user_id: int, /) -> Optional[Member]:
        """Returns a member with the given ID.

        Parameters
        -----------
        user_id: :class:`int`
            The ID to search for.

        Returns
        --------
        Optional[:class:`Member`]
            The member or ``None`` if not found.
        """
        return self._members.get(user_id)

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
        except (KeyError, TypeError, ValueError):
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
        privacy_level: Optional[GuildScheduledEventPrivacyLevel] = MISSING,
        scheduled_start_time: Optional[datetime] = MISSING,
        scheduled_end_time: Optional[datetime] = MISSING,
        entity_type: Optional[GuildScheduledEventType] = MISSING,
        location: Optional[str] = MISSING,
        speakers: Optional[List[Union[Member, User]]] = MISSING,
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
        privacy_level: Optional[:class:`GuildScheduledEventPrivacyLevel`]
            The event privacy level.
        scheduled_start_time: Optional[:class:`datetime.datetime`]
            The new scheduled start time, timezone must be UTC. If not it will be converted
            automatically.
        scheduled_end_time: Optional[:class:`datetime.datetime`]
            The new scheduled end time, timezone must be UTC.
            If not it will be converted automatically.
            It would be used if the event is a :attr:`GuildScheduledEventType.location` event.
        entity_type: Optional[:class:`GuildScheduledEventType`]
            The new ``entity type`` or ``type`` for the event.
        location: Optional[:class:`str`]
            The new location for the event. It would be used if the event is a
            :attr:`GuildScheduledEventType.location` event.
        speakers: Optional[List[Union[:class:`Member`, :class:`User`]]]
            The new list of speakers for the event. It would be used if the event is a
            :attr:`GuildScheduledEventType.stage_instance` event.

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

        fields = {}

        if name is not MISSING:
            fields["name"] = name

        if description is not MISSING:
            fields["description"] = description

        if channel is not MISSING:
            fields["channel_id"] = str(channel.id)

        privacy_level = GuildScheduledEventPrivacyLevel.members_only.value
        if privacy_level is not MISSING and privacy_level is not None:
            privacy_level = privacy_level.value
        fields["privacy_level"] = privacy_level

        if scheduled_start_time is not MISSING:
            scheduled_start_time = scheduled_start_time.replace(tzinfo=timezone.utc).isoformat()
            fields["scheduled_start_time"] = scheduled_start_time.isoformat()

        entity_type = self.type.value
        if entity_type is not MISSING and entity_type is not None:
            entity_type = entity_type.value
        fields["entity_type"] = entity_type

        entity_metadata = {}
        if location is not MISSING:
            entity_metadata["location"] = location
        elif self.location is not None:
            entity_metadata["location"] = self.location
        if speakers is not MISSING:
            entity_metadata["speakers_ids"] = [str(s.id) for s in speakers]
        elif self.speakers:
            entity_metadata["speakers_ids"] = [str(s.id) for s in self.speakers]

        if not entity_metadata:
            entity_metadata = None
        fields["entity_metadata"] = entity_metadata
        if entity_type == GuildScheduledEventType.location.value:
            if scheduled_end_time is not MISSING:
                scheduled_end_time = scheduled_end_time.replace(tzinfo=timezone.utc).isoformat()
                fields["scheduled_end_time"] = scheduled_end_time.isoformat()
            elif self.end_time is not None:
                fields["scheduled_end_time"] = self.end_time.isoformat()

        guild = self.guild
        data = await http.create_guild_scheduled_event(guild.id, **fields)
        try:
            channel = guild.get_channel(int(data["channel_id"]))
        except (KeyError, TypeError, ValueError):
            channel = None
        else:
            guild = channel or guild
        self._update(guild, data)
        return self

    async def delete(self) -> None:
        """|coro|

        Deletes the guild event.

        You must have the :attr:`~Permissions.manage_events` permission
        to be able to delete the guild event.

        Raises
        --------
        Forbidden
            You do not have permissions to delete the guild event.
        HTTPException
            Deleting the guild event failed.
        """

        await self._state.http.delete_guild_scheduled_event(self.id)
