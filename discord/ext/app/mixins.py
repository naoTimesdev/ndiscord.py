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

from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union, overload

from ._types import CogT, Check
from .context import ApplicationContext
from .core import ApplicationCommand, MessageCommand, SlashCommand, UserCommand, command, AppCommandT
from .errors import ApplicationRegistrationError

import discord
from discord.interactions import Interaction
from discord.enums import ApplicationCommandType, InteractionType
from discord.errors import DiscordException

T = TypeVar('T')
DecoApp = Callable[..., T]

__all__ = (
    'ApplicationCommandMixin',
)

MISSING: Any = discord.utils.MISSING
AppCommand = Union[SlashCommand, UserCommand, MessageCommand]


class ApplicationCommandFactory:
    def __init__(self):
        self._slash_commands: Dict[str, SlashCommand] = {}
        self._user_commands: Dict[str, UserCommand] = {}
        self._message_commands: Dict[str, MessageCommand] = {}

    @property
    def slash_commands(self):
        return self._slash_commands

    @property
    def user_commands(self):
        return self._user_commands

    @property
    def message_commands(self):
        return self._message_commands

    slash = slash_commands
    user = user_commands
    message = message_commands

    def all_commands(self) -> List[ApplicationCommand]:
        slash_commands = list(self._slash_commands.values())
        user_commands = list(self._user_commands.values())
        message_commands = list(self._message_commands.values())
        return slash_commands + user_commands + message_commands

    values = all_commands

    def add_command(self, command: AppCommandT):
        if command.type is None:
            return
        if command.type == ApplicationCommandType.slash:
            if command.name in self._slash_commands:
                raise ApplicationRegistrationError(command.name)
            self._slash_commands[command.name] = command
        elif command.type == ApplicationCommandType.message:
            if command.name in self._message_commands:
                raise ApplicationRegistrationError(command.name)
            self._message_commands[command.name] = command
        elif command.type == ApplicationCommandType.user:
            if command.name in self._user_commands:
                raise ApplicationRegistrationError(command.name)
            self._user_commands[command.name] = command

    def get_command(self, name: str, type: ApplicationCommandType) -> Optional[AppCommand]:
        location_enum = {
            ApplicationCommandType.slash: self._slash_commands,
            ApplicationCommandType.message: self._message_commands,
            ApplicationCommandType.user: self._user_commands,
        }
        return location_enum[type].get(name, None)

    def find_command(self, name: str) -> Optional[AppCommand]:
        if name in self._slash_commands:
            return self._slash_commands[name]
        elif name in self._message_commands:
            return self._message_commands[name]
        elif name in self._user_commands:
            return self._user_commands[name]
        return None

    def _remove_by_name(self, name: str, location: ApplicationCommandType = None):
        location_enum = {
            ApplicationCommandType.slash: self._slash_commands,
            ApplicationCommandType.message: self._message_commands,
            ApplicationCommandType.user: self._user_commands,
        }
        if location is not None:
            try:
                return location_enum[location].pop(name)
            except KeyError:
                return

        try:
            return self._slash_commands.pop(name)
        except KeyError:
            pass
        try:
            return self._user_commands.pop(name)
        except KeyError:
            pass
        try:
            return self._message_commands.pop(name)
        except KeyError:
            pass
        return

    def remove_command(self, command: Union[str, AppCommandT]) -> Optional[AppCommand]:
        if isinstance(command, str):
            return self._remove_by_name(command)
        elif isinstance(command, ApplicationCommand):
            return self._remove_by_name(command.name, command.type)
        return None

class ApplicationCommandMixin(Generic[CogT]):
    _debug_guilds: List[int]
    _app_factories: ApplicationCommandFactory
    _pending_registration: List[ApplicationCommand] = []

    def __new__(cls: Type["ApplicationCommandMixin"], *args, **kwargs) -> "ApplicationCommandMixin":
        debug_guild = kwargs.pop("debug_guild", None)
        debug_guilds = kwargs.pop("debug_guilds", None)

        self = super().__new__(cls)

        _debug_guild = []
        if isinstance(debug_guild, int):
            _debug_guild.append(debug_guild)
        elif isinstance(debug_guilds, list):
            for guild in debug_guilds:
                if isinstance(guild, int):
                    _debug_guild.append(guild)

        self._debug_guilds = _debug_guild
        self._app_factories = ApplicationCommandFactory()
        self._pending_registration = []

        return self

    @property
    def all_applications(self):
        return self._app_factories

    @property
    def debug_guilds(self):
        """List[:class:`int`]:
        Get the list of guilds that are being used for debugging purpose.
        """
        return self._debug_guilds

    def add_application(self, command: AppCommandT) -> None:
        """
        Register a new application command.

        Parameters
        ------------
        command: :class:`.ApplicationCommand`
            The command to register.

        """
        if not isinstance(command.guild_ids, list) and len(self.debug_guilds) > 0:
            command.guild_ids = self.debug_guilds
        elif isinstance(command.guild_ids, list):
            command.guild_ids.extend(self.debug_guilds)
        self._pending_registration.append(command)

    def remove_application(self, command: AppCommandT) -> Optional[AppCommandT]:
        """
        Remove command from the list of registered commands.

        Parameters
        ------------
        command: :class:`.ApplicationCommand`
            The command to register.

        """
        pop_out = self._app_factories.remove_command(command)
        try:
            pop_out = self._pending_registration.pop(self._pending_registration.index(command))
        except ValueError:
            pass
        return pop_out

    def register_application(self, command: AppCommandT):
        """
        Register the command to the factories and remove from pending section.
        Please make sure the app already been registered to Discord.

        Parameters
        -----------
        command: :class:`.ApplicationCommand`
            The command to register.
        """
        if command in self._pending_registration:
            self._pending_registration.remove(command)
        if command.id is None:
            raise TypeError(f'Cannot register {command.name} because missing application ID.')
        self._app_factories.add_command(command)

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

        interaction_type = interaction.data.get('type', 1)
        inter_name = interaction.data.get('name')

        command = self._app_factories.get_command(inter_name, ApplicationCommandType(interaction_type))
        if command is None:
            self.dispatch('unknown_application', interaction)
        else:
            ctx = await self.get_application_context(interaction)
            ctx.command = command
            self.dispatch('application_before_invoke', ctx)
            try:
                await ctx.command.invoke(ctx)
            except DiscordException as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch('application_after_invoke', ctx)

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
