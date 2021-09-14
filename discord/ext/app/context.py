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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypeVar, Union

import discord.abc
import discord.utils
from discord import Guild, Member, User
from discord.interactions import (
    Interaction,
    InteractionChannel,
    InteractionResponse
)
from discord.state import ConnectionState
from discord.user import ClientUser
from discord.voice_client import VoiceProtocol

if TYPE_CHECKING:
    from discord.client import Client
    from discord.ext.commands import AutoShardedBot, Bot, Cog

__all__ = (
    'ApplicationContext'
)

MISSING: Any = discord.utils.MISSING

BotT = TypeVar('BotT', bound="Union[Bot, AutoShardedBot, Client]")
CogT = TypeVar('CogT', bound="Cog")


class ApplicationContext(discord.abc.Messageable):
    """Represents the context in which a application command is being invoked under.

    This class contains a lot of meta data to help you understand more about
    the invocation context. This class is not created manually and is instead
    passed around to commands as the first parameter.

    This class implements the :class:`~discord.abc.Messageable` ABC.

    Attributes
    ----------
    bot: :class:`Bot`
        The bot which is invoking the command.
    interaction: :class:`.Interaction`
        The interaction object which is used to interact with the user.
    args: :class:`list`
        The list of transformed arguments that were passed into the command.
        If this is accessed during the :func:`.on_application_command_error` event
        then this list could be incomplete.
    kwargs: :class:`dict`
        A dictionary of transformed arguments that were passed into the command.
        Similar to :attr:`args`, if this is accessed in the
        :func:`.on_application_command_error` event then this dict could be incomplete.
    command: :class:`.ApplicationCommand`
        The command or application command that are being executed.
        If it's not passed yet, it will be None.
    deferred: :class:`bool`
        Is the command already deferred or no?
    command_failed: :class:`bool`
        A boolean that indicates if this command failed to be parsed, checked,
        or invoked.
    """

    def __init__(
        self,
        *,
        bot: BotT,
        interaction: Interaction,
        args: List[Any] = MISSING,
        kwargs: Dict[str, Any] = MISSING,
        command: Any = MISSING,
        command_failed: bool = False
    ) -> None:
        self.bot: BotT = bot
        self.interaction: Interaction = interaction
        self.args: List[Any] = args
        self.kwargs: Dict[str, Any] = kwargs
        self.command_failed: bool = command_failed
        self.command: Any = command

        self.deferred: bool = False
        self._state: ConnectionState = self.interaction._state

    @property
    def cog(self) -> Optional[CogT]:
        """Optional[:class:`.Cog`]: Returns the cog associated with this context's command. None if it does not exist."""
        if self.command is None:
            return None
        return self.command.cog

    @discord.utils.cached_property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`.Guild`]: Returns the guild associated with this context's command. None if not available."""
        return self.interaction.guild

    @discord.utils.cached_property
    def channel(self) -> Optional[InteractionChannel]:
        """Optional[:class:`.abc.MessageableChannel`]: Returns the channel associated with this context's command. None if not available."""
        return self.interaction.channel

    @discord.utils.cached_property
    def author(self) -> Optional[Union[User, Member]]:
        """Optional[Union[:class:`~discord.User`, :class:`.Member`]]:
        Returns the author associated with this context's command. Shorthand for :attr:`.Message.author`
        """
        return self.interaction.user

    @discord.utils.cached_property
    def me(self) -> Union[Member, ClientUser]:
        """Union[:class:`.Member`, :class:`.ClientUser`]:
        Similar to :attr:`.Guild.me` except it may return the :class:`.ClientUser` in private message contexts.
        """
        # bot.user will never be None at this point.
        return self.guild.me if self.guild is not None else self.bot.user  # type: ignore

    @property
    def voice_client(self) -> Optional[VoiceProtocol]:
        r"""Optional[:class:`.VoiceProtocol`]: A shortcut to :attr:`.Guild.voice_client`\, if applicable."""
        g = self.guild
        return g.voice_client if g else None

    @discord.utils.cached_property
    def response(self) -> InteractionResponse:
        """:class:`InteractionResponse`: Shortcut for `.Interaction.response`
        """
        return self.interaction.response

    @property
    def followup(self):
        return self.interaction.followup

    @property
    def respond(self):
        if self.deferred:
            return self.edit
        return self.followup.send if self.response.is_done() else self.interaction.response.send_message

    @property
    def edit(self):
        return self.interaction.edit_original_message

    @property
    def defer(self):
        return self.interaction.response.defer

    @property
    def pong(self):
        return self.interaction.response.pong

    send = respond
