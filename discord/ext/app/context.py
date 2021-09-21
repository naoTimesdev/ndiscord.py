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

from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Union

import discord.abc
import discord.utils
from discord.guild import Guild
from discord.interactions import Interaction, InteractionResponse
from discord.member import Member
from discord.state import ConnectionState
from discord.user import ClientUser, User
from discord.voice_client import VoiceProtocol

from ._types import AppCommandT, BotT, CogT

if TYPE_CHECKING:
    from discord.embeds import Embed
    from discord.file import File
    from discord.interactions import InteractionChannel
    from discord.mentions import AllowedMentions
    from discord.ui import View

__all__ = ("ApplicationContext",)

MISSING: Any = discord.utils.MISSING


class ApplicationContext(discord.abc.Messageable, Generic[CogT, BotT, AppCommandT]):
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
        If this is accessed during the :func:`.on_application_error` event
        then this list could be incomplete.
    kwargs: :class:`dict`
        A dictionary of transformed arguments that were passed into the command.
        Similar to :attr:`args`, if this is accessed in the
        :func:`.on_application_error` event then this dict could be incomplete.
    command: Union[:class:`.SlashCommand`, :class:`.UserCommand`, :class:`.MessageCommand`]
        The command or application command that are being executed.
        If it's not passed yet, it will be None.
    command_failed: :class:`bool`
        A boolean that indicates if this command failed to be parsed, checked,
        or invoked.
    invoked_subcommand: Optional[:class:`.SlashCommand`]
        The subcommand that was invoked, if any.
    """

    def __init__(
        self,
        *,
        bot: BotT,
        interaction: Interaction,
        args: List[Any] = MISSING,
        kwargs: Dict[str, Any] = MISSING,
        command: AppCommandT = MISSING,
        command_failed: bool = False,
    ) -> None:
        self.bot: BotT = bot
        self.interaction: Interaction = interaction
        self.args: List[Any] = args
        self.kwargs: Dict[str, Any] = kwargs
        self.command_failed: bool = command_failed
        self.command: AppCommandT = command

        # Subcommand stuff for /slash command
        self.invoked_subcommand: Optional[AppCommandT] = None

        self._deferred: bool = False
        self._state: ConnectionState = self.interaction._state

    @property
    def cog(self) -> Optional[CogT]:
        """Optional[:class:`.Cog`]: Returns the cog associated with this context's command.
        None if it does not exist.
        """
        if self.command is None:
            return None
        return self.command.cog

    @property
    def invoked_with(self) -> Optional[str]:
        """invoked_with: Optional[:class:`str`]: The original string that the user used to invoke the command.
        Might be none if the command is context menu.
        """
        return self.interaction.data.get("name")

    @property
    def responded(self) -> bool:
        """:class:`bool`: Indicates whether an interaction response has been done before.

        An interaction can only be responded to once.
        """
        return self.response.is_done()

    @property
    def deferred(self) -> bool:
        """:class:`bool`: Indicates if the interaction already been deferred.

        If it's already deferred, when user use :meth:`.respond` or :meth:`.send`
        it will use :meth:`.edit` to edit the response instead.
        """
        return self._deferred

    @discord.utils.cached_property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`.Guild`]: Returns the guild associated with this context's command.
        None if not available.
        """
        return self.interaction.guild

    @discord.utils.cached_property
    def channel(self) -> Optional["InteractionChannel"]:
        """Optional[Union[:class:`~discord.abc.GuildChannel`, :class:`.PartialMessageable`, :class:`.Thread`]: Returns
        the channel associated with this context's command. None if not available.
        """
        return self.interaction.channel

    @discord.utils.cached_property
    def author(self) -> Optional[Union[User, Member]]:
        """Optional[Union[:class:`~discord.User`, :class:`.Member`]]: Returns the author associated with this
        context's command. Shorthand for :attr:`.Message.author`
        """
        return self.interaction.user

    @discord.utils.cached_property
    def me(self) -> Union[Member, ClientUser]:
        """Union[:class:`.Member`, :class:`.ClientUser`]: Similar to :attr:`.Guild.me` except it may return
        the :class:`.ClientUser` in private message contexts.
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
        """:class:`.InteractionResponse`: Shortcut for :attr:`.Interaction.response`"""
        return self.interaction.response

    @property
    def followup(self):
        """:class:`.Webhook`: Returns the follow up webhook for follow up interactions."""
        return self.interaction.followup

    @property
    def respond(self):
        """|coro|

        Respond to the interaction.

        This property is a shortcut for :attr:`.Webhook.send`, :meth:`~.InteractionResponse.send_message`,
        or :attr:`~.Interaction.edit_original_message`.

        It will automatically selected the appropriate method based on the
        current state of the interaction.

        If the interaction already deferred, it will use :meth:`.edit` to edit the response instead.
        If the interaction is already responded, it will use :meth:`~.Webhook.send` to respond
        while if it haven't it will use :attr:`.InteractionResponse.send_message` to respond.
        """
        if self.deferred:
            return self.edit
        return self.followup.send if self.response.is_done() else self.interaction.response.send_message

    @discord.utils.copy_doc(Interaction.edit_original_message)
    def edit(
        self,
        content: Optional[str] = MISSING,
        *,
        embeds: List["Embed"] = MISSING,
        embed: Optional["Embed"] = MISSING,
        file: "File" = MISSING,
        files: List["File"] = MISSING,
        view: Optional["View"] = MISSING,
        allowed_mentions: Optional["AllowedMentions"] = None,
    ):
        return self.interaction.edit_original_message(
            content=content,
            embeds=embeds,
            embed=embed,
            file=file,
            files=files,
            view=view,
            allowed_mentions=allowed_mentions,
        )

    @discord.utils.copy_doc(InteractionResponse.defer)
    async def defer(self, *, ephemeral: bool = False):
        await self.interaction.response.defer(ephemeral=ephemeral)
        self._deferred = True

    @discord.utils.copy_doc(Interaction.delete_original_message)
    def delete(self):
        return self.interaction.delete_original_message

    @discord.utils.copy_doc(InteractionResponse.pong)
    def pong(self):
        return self.interaction.response.pong

    send = respond
