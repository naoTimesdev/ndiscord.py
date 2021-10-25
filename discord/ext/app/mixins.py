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

import sys
import traceback
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union, overload

import discord
from discord.enums import ApplicationCommandType, InteractionType
from discord.errors import DiscordException
from discord.interactions import Interaction

from ._types import AppCommandT, BotT, Check, CogT, ContextT
from .context import ApplicationContext
from .core import ApplicationCommand, MessageCommand, SlashCommand, UserCommand, command
from .errors import ApplicationCommandError, ApplicationRegistrationError

T = TypeVar("T")
DecoApp = Callable[..., T]

__all__ = ("ApplicationCommandMixin",)

MISSING: Any = discord.utils.MISSING
AppCommand = Union[SlashCommand[CogT, BotT], UserCommand[CogT, BotT], MessageCommand[CogT, BotT]]


class ApplicationCommandFactory(Generic[CogT, BotT, ContextT, AppCommandT]):
    """A "factory" or collector of application commands.

    These factory should not be created manually, it will be called from
    :class:`.ApplicationCommandMixin`.

    Attributes
    -----------
    slash_commands: Dict[:class:`str`, :class:`.SlashCommand`]
        All slash commands registered with this factory.
    user_commands: Dict[:class:`str`, :class:`.UserCommand`]
        All user commands registered with this factory.
    message_commands: Dict[:class:`str`, :class:`.MessageCommand`]
        All message commands registered with this factory.
    """

    def __init__(self):
        self._slash_commands: Dict[str, SlashCommand[CogT, BotT]] = {}
        self._user_commands: Dict[str, UserCommand[CogT, BotT]] = {}
        self._message_commands: Dict[str, MessageCommand[CogT, BotT]] = {}

    @property
    def slash_commands(self):
        return self._slash_commands

    @property
    def user_commands(self):
        return self._user_commands

    @property
    def message_commands(self):
        return self._message_commands

    def all_commands(self) -> List[AppCommandT]:
        """List[:class:`.ApplicationCommand`]: Get all commands from this factory."""
        slash_commands = list(self._slash_commands.values())
        user_commands = list(self._user_commands.values())
        message_commands = list(self._message_commands.values())
        return slash_commands + user_commands + message_commands

    values = all_commands

    def add_command(self, command: AppCommandT):
        """Add a new command to the factories.

        If the command already exist, it will raise an :exc:`.ApplicationRegistrationError`.

        Parameters
        -----------
        command: :class:`.ApplicationCommand` derived
            The command to register.

        Raises
        ---------
        ApplicationRegistrationError
            Raised when you're trying to register a command with the same name
            as other command that already been registered.
        """
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
        """Get a command from the factory.

        Parameters
        -----------
        name: :class:`str`
            The command name to search
        type: :class:`.ApplicationCommandType`
            The type of command to search for.

        Returns
        ---------
        Optional[:class:`.ApplicationCommand`] derived
            The command that was requested, or ``None`` if not found.
        """
        location_enum = {
            ApplicationCommandType.slash: self._slash_commands,
            ApplicationCommandType.message: self._message_commands,
            ApplicationCommandType.user: self._user_commands,
        }
        return location_enum[type].get(name, None)

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
        """Remove a command from the factory.

        Parameters
        -----------
        command: Union[:class:`str`, :class:`.ApplicationCommand` derived]
            The command to search for, it will try to match by name.
            If you provide a string, it will try to guess where the command is.

        Returns
        --------
        Optional[:class:`.ApplicationCommand`]
            The command that was removed, if ``None`` it means the command doesn't exist.
        """
        if isinstance(command, str):
            return self._remove_by_name(command)
        elif isinstance(command, ApplicationCommand):
            return self._remove_by_name(command.name, command.type)
        return None


class ApplicationCommandMixin(Generic[CogT, BotT, AppCommandT, ContextT]):
    """A mixin that provides application commands to the bot.

    These mixin should not be created manually, this will be used by :class:`.Client`
    or by :class:`~discord.ext.commands.Bot`.

    .. versionadded:: 2.0

    Attributes
    ------------

    all_applications: :class:`.ApplicationCommandFactory`
        A collection of registered commands that the bot knows.
    debug_guilds: List[:class:`int`]
        Get the list of guilds that are being used for debugging purpose.
    """

    _debug_guilds: List[int]
    _app_factories: ApplicationCommandFactory[CogT, BotT, ContextT, AppCommandT]
    _pending_registration: List[ApplicationCommand[CogT, BotT]] = []

    def __new__(
        cls: Type[ApplicationCommandMixin], *args, **kwargs
    ) -> ApplicationCommandMixin[CogT, BotT, AppCommandT]:
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
            raise TypeError(f"Cannot register {command.name} because missing application ID.")
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
        :meth:`ApplicationCommandMixin.application_command` and runs :meth:`ApplicationCommand.invoke` on it.
        If no matching command was found, it replies to the interaction with a default message.

        .. versionadded:: 2.0

        Parameters
        -----------
        interaction: :class:`discord.Interaction`
            The interaction to process
        """
        _VALID_TYPE = (InteractionType.application_command, InteractionType.autocomplete)
        if interaction.type not in _VALID_TYPE:
            return

        interaction_type = interaction.data.get("type", 1)
        inter_name = interaction.data.get("name")

        command = self._app_factories.get_command(inter_name, ApplicationCommandType(interaction_type))
        if command is None:
            self.dispatch("unknown_application", interaction)
        else:
            ctx = await self.get_application_context(interaction)
            ctx.command = command
            self.dispatch("application", ctx)
            try:
                await ctx.command.invoke(ctx)
            except DiscordException as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch("application_completion", ctx)

    async def get_application_context(
        self, interaction: Interaction, cls: Optional[ApplicationContext[BotT, CogT]] = None
    ) -> ApplicationContext[BotT, CogT]:
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
            The invocation context. The type of this can change via the
            ``cls`` parameter.
        """
        if cls is None:
            cls = ApplicationContext
        return cls(bot=self, interaction=interaction)

    async def on_interaction(self, interaction: Interaction) -> None:
        """|coro|

        This event handle should handle all interaction coming from Discord.
        This would pass the information into :meth:`.process_application_commands`

        If you're overriding this, please dont forget to call the :meth:`.process_application_commands`
        or the application wont work.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction to process
        """
        await self.process_application_commands(interaction)

    async def on_application_error(
        self, context: ApplicationContext[BotT, CogT], exception: ApplicationCommandError
    ) -> None:
        """|coro|

        The default command error handler provided by the bot.

        By default this prints to :data:`sys.stderr` however it could be
        overridden to have a different implementation.

        This only fires if you do not specify any listeners for command error.
        """
        extra_events: dict = getattr(self, "extra_events", None)
        if extra_events is not None and extra_events.get("on_application_error", None):
            return

        command = context.command
        if command and command.has_error_handler():
            return

        cog = context.cog
        if cog and cog.has_error_handler():
            return

        print(f"Ignoring exception in command {context.command}:", file=sys.stderr)
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)

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
        """A shortcut decorator that invokes :func:`~discord.ext.app.command` and adds it to
        the internal command list via :meth:`~.ApplicationCommandMixin.add_application`.

        .. versionadded:: 2.0

        Returns
        --------
        Callable[..., :class:`ApplicationCommand`]
            A decorator that converts the provided method into an :class:`.ApplicationCommand`,
            adds it to the bot, then returns it.
        """

        def decorator(func) -> AppCommandT:
            result = command(**kwargs)(func)
            self.add_application(result)
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
    ) -> DecoApp[SlashCommand[CogT, BotT]]:
        ...

    def slash_command(self, **kwargs):
        """A shortcut decorator that invokes :func:`~discord.ext.app.command` and adds it to
        the internal command list via :meth:`~.ApplicationCommandMixin.add_application`.
        This shortcut is made specifically for :class:`.SlashCommand`.

        .. versionadded:: 2.0

        Parameters
        ------------
        name: Optional[:class:`str`]
            The name of the command. Defaults to the name of the method.
        description: Optional[:class:`str`]
            A short description of the command.
        guild_ids: Optional[List[:class:`int`]]
            Guild IDs where the command can be run on. Setting this will make the command
            only usable from this guild.
        checks: Optional[List[Callable[[:class:`.ApplicationContext`], :class:`bool`]]]
            A list of predicates that must be true for the command to be invoked.

        Returns
        --------
        Callable[..., :class:`.SlashCommand`]
            A decorator that converts the provided method into a :class:`.SlashCommand`,
            adds it to the bot, then returns it.
        """
        return self.application_command(cls=SlashCommand, **kwargs)

    @overload
    def user_command(
        self,
        *,
        name: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[UserCommand[CogT, BotT]]:
        ...

    def user_command(self, **kwargs):
        """A shortcut decorator that invokes :func:`~discord.ext.app.command` and adds it to
        the internal command list via :meth:`~.ApplicationCommandMixin.add_application`.
        This shortcut is made specifically for :class:`.UserCommand`.

        .. versionadded:: 2.0

        Parameters
        ------------
        name: Optional[:class:`str`]
            The name of the command. Defaults to the name of the method.
        guild_ids: Optional[List[:class:`int`]]
            Guild IDs where the command can be run on. Setting this will make the command
            only usable from this guild.
        checks: Optional[List[Callable[[:class:`.ApplicationContext`], :class:`bool`]]]
            A list of predicates that must be true for the command to be invoked.

        Returns
        --------
        Callable[..., :class:`.UserCommand`]
            A decorator that converts the provided method into a :class:`.UserCommand`,
            adds it to the bot, then returns it.
        """
        return self.application_command(cls=UserCommand, **kwargs)

    @overload
    def message_command(
        self,
        *,
        name: Optional[str] = MISSING,
        guild_ids: Optional[List[int]] = MISSING,
        checks: Optional[List[Check]] = MISSING,
    ) -> DecoApp[MessageCommand[CogT, BotT]]:
        ...

    def message_command(self, **kwargs):
        """A shortcut decorator that invokes :func:`~discord.ext.app.command` and adds it to
        the internal command list via :meth:`~.ApplicationCommandMixin.add_application`.
        This shortcut is made specifically for :class:`.MessageCommand`.

        .. versionadded:: 2.0

        Parameters
        ------------
        name: Optional[:class:`str`]
            The name of the command. Defaults to the name of the method.
        guild_ids: Optional[List[:class:`int`]]
            Guild IDs where the command can be run on. Setting this will make the command
            only usable from this guild.
        checks: Optional[List[Callable[[:class:`.ApplicationContext`], :class:`bool`]]]
            A list of predicates that must be true for the command to be invoked.

        Returns
        --------
        Callable[..., :class:`.MessageCommand`]
            A decorator that converts the provided method into a :class:`.MessageCommand`,
            adds it to the bot, then returns it.
        """
        return self.application_command(cls=MessageCommand, **kwargs)
