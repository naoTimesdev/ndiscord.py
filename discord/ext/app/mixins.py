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

from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, overload

from ._types import CogT, Check
from .context import ApplicationContext
from .core import ApplicationCommand, MessageCommand, SlashCommand, UserCommand, command, AppCommandT

import discord
from discord.interactions import Interaction
from discord.enums import InteractionType
from discord.errors import DiscordException

T = TypeVar('T')
DecoApp = Callable[..., T]

MISSING: Any = discord.utils.MISSING


class ApplicationCommandMixin(Generic[CogT]):
    def __init__(self, *args, **kwargs: Any) -> None:
        debug_guild = kwargs.pop("debug_guild", None)
        debug_guilds = kwargs.pop("debug_guilds", None)

        _debug_guild = []
        if isinstance(debug_guild, int):
            _debug_guild.append(debug_guild)
        elif isinstance(debug_guilds, list):
            for guild in debug_guilds:
                if isinstance(guild, int):
                    _debug_guild.append(guild)

        self._debug_guilds = _debug_guild
        self.all_applications: Dict[str, ApplicationCommand] = {}
        self._pending_registration: List[ApplicationCommand] = []
        super().__init__(*args, **kwargs)

    @property
    def debug_guilds(self):
        """List[:class:`int`]:
        Get the list of guilds that are being used for debugging purpose.
        """
        return self._debug_guilds

    def add_application(self, command: AppCommandT) -> None:
        command.guild_ids.extend(self.debug_guilds)
        self._pending_registration.append(command)
        self.all_applications[command.name] = command

    def remove_application(self, command: AppCommandT) -> Optional[AppCommandT]:
        pop_out = None
        try:
            pop_out = self.all_applications.pop(command.name)
        except KeyError:
            pass
        try:
            pop_out = self._pending_registration.pop(self._pending_registration.index(command))
        except ValueError:
            pass
        return pop_out

    async def process_application_commands(self, interaction: Interaction):
        """|coro|
        This function processes the commands that have been registered
        to the bot and other groups. Without this coroutine, none of the
        commands will be triggered.

        By default, this coroutine is called inside the :func:`.on_interaction`
        event. If you choose to override the :func:`.on_interaction` event, then
        you should invoke this coroutine as well.

        This function finds a registered command matching the interaction id from
        :attr:`.ApplicationCommandMixin.application_commands` and runs :meth:`ApplicationCommand.invoke` on it. If no matching
        command was found, it replies to the interaction with a default message.

        .. versionadded:: 2.0

        Parameters
        -----------
        interaction: :class:`discord.Interaction`
            The interaction to process
        """
        if not interaction.type != InteractionType.application_command:
            return

        try:
            command = self.all_applications[interaction.data.get('name')]
        except KeyError:
            self.dispatch('unknown_application')
        else:
            ctx = await self.get_application_context(interaction)
            ctx.command = command
            self.dispatch('application_command', ctx)
            try:
                await ctx.command.invoke(ctx)
            except DiscordException as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch('application_command_finished', ctx)

    async def get_application_context(self, interaction: Interaction, cls = None) -> ApplicationContext:
        r"""|coro|

        Returns the invocation context from the interaction.
        This is a more low-level counter-part for :meth:`.process_application_commands`
        to allow users more fine grained control over the processing.

        Parameters
        -----------
        interaction: :class:`discord.Interaction`
            The interaction to get the invocation context from.
        cls
            The factory class that will be used to create the context.
            By default, this is :class:`.ApplicationContext`. Should a custom
            class be provided, it must be similar enough to
            :class:`.ApplicationContext`\'s interface.

        Returns
        --------
        :class:`.ApplicationContext`
            The invocation context. Tye type of this can change via the
            ``cls`` parameter.
        """
        if cls is None:
            cls = ApplicationContext
        return cls(self, bot=self, interaction=interaction)

    @overload
    def application_command(
        self,
        *,
        cls: Type[AppCommandT] = SlashCommand,
        name: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[AppCommandT]:
        ...

    @overload
    def application_command(
        self,
        *,
        cls: Type[AppCommandT] = SlashCommand,
        name: Optional[str] = MISSING,
        description: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[AppCommandT]:
        ...

    def application_command(self, **kwargs) -> DecoApp[AppCommandT]:
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list via :meth:`~.ApplicationCommandMixin.add_application`.

        .. versionadded:: 2.0

        Returns
        --------
        Callable[..., :class:`ApplicationCommand`]
            A decorator that converts the provided method into an :class:`.ApplicationCommand`, adds it to the bot,
            then returns it.
        """

        def decorator(func) -> AppCommandT:
            kwargs.setdefault("parent", self)
            result = command(**kwargs)(func)
            setattr(result, 'parent', self)
            self.add_application_command(result)
            return result

        return decorator

    @overload
    def slash_command(
        self,
        *,
        name: Optional[str] = MISSING,
        description: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[SlashCommand]:
        ...

    def slash_command(self, **kwargs):
        """A shortcut decorator that invokes :func:`.ApplicationCommandMixin.command` and adds it to
        the internal command list via :meth:`~.ApplicationCommandMixin.add_application_command`.
        This shortcut is made specifically for :class:`.SlashCommand`.
        .. versionadded:: 2.0

        Returns
        --------
        Callable[..., :class:`SlashCommand`]
            A decorator that converts the provided method into a :class:`.SlashCommand`, adds it to the bot,
            then returns it.
        """
        return self.application_command(cls=SlashCommand, **kwargs)

    @overload
    def user_command(
        self,
        *,
        name: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[UserCommand]:
        ...

    def user_command(self, **kwargs):
        """Decorator for user commands that invokes :func:`application_command`.

        .. versionadded:: 2.0

        Returns
        --------
        Callable[..., :class:`UserCommand`]
            A decorator that converts the provided method into a :class:`.UserCommand`.
        """
        return self.application_command(cls=UserCommand, **kwargs)

    @overload
    def message_command(
        self,
        *,
        name: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[MessageCommand]:
        ...

    def message_command(self, **kwargs):
        """Decorator for message commands that invokes :func:`application_command`.

        .. versionadded:: 2.0

        Returns
        --------
        Callable[..., :class:`MessageCommand`]
            A decorator that converts the provided method into a :class:`.MessageCommand`.
        """
        return self.application_command(cls=MessageCommand, **kwargs)

    command = application_command
