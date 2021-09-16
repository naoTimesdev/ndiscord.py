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

import asyncio
import functools
import inspect
from collections import OrderedDict
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    overload
)

import discord
from discord.enums import ApplicationCommandType, SlashCommandOptionType
from discord.errors import ClientException
from discord.member import Member
from discord.message import Message
from discord.user import User
from typing_extensions import Concatenate, ParamSpec, TypeGuard

from ._types import (
    AcceptedInputType,
    ApplicationCallback,
    Check,
    CogT,
    Coro,
    Error,
    Hook,
    _BaseApplication
)
from .context import ApplicationContext
from .errors import *

__all__ = (
    'ApplicationCommand',
    'Option',
    'OptionChoice',
    'SlashCommand',
    'ContextMenuApplication',
    'UserCommand',
    'MessageCommand',
    'option',
    'application_command',
    'slash_command',
    'user_command',
    'message_command',
    'command',
)

T = TypeVar('T')
AppCommandT = TypeVar('AppCommandT', bound="Union[ApplicationCommand, SlashCommand, UserCommand, MessageCommand]")
ContextT = TypeVar('ContextT', bound="ApplicationContext")
ErrorT = TypeVar('ErrorT', bound="Error")
HookT = TypeVar('HookT', bound="Hook")
SubAppCommandT = TypeVar('SubAppCommandT')
DecoApp = Callable[..., T]
FuncT = TypeVar('FuncT', bound=Callable[..., Any])
P = ParamSpec('P')

AppCommandWrap = Callable[
    [
        Union[
            Callable[Concatenate[CogT, ContextT, P], Coro[T]],
            Callable[Concatenate[ContextT, P], Coro[T]],
        ]
    ],
    AppCommandT
]

MISSING: Any = discord.utils.MISSING


def get_signature_parameters(func: ApplicationCallback):
    return OrderedDict(inspect.signature(func).parameters)


def wrap_callback(coro: Hook):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
        try:
            ret = await coro(*args, **kwargs)
        except ApplicationCommandError:
            raise
        except asyncio.CancelledError:
            return
        except Exception as exc:
            raise ApplicationCommandInvokeError(exc) from exc
        return ret
    return wrapped


def hooked_wrapped_callback(command: AppCommandT, ctx: ApplicationContext, coro: Coro[ApplicationCallback]):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
        try:
            ret = await coro(*args, **kwargs)
        except ApplicationCommandError:
            ctx.command_failed = True
            raise
        except asyncio.CancelledError:
            ctx.command_failed = True
            return
        except Exception as exc:
            ctx.command_failed = True
            raise ApplicationCommandInvokeError(exc) from exc
        finally:
            await command.call_after_hooks(ctx)
        return ret
    return wrapped


class ApplicationCommand(_BaseApplication):
    type: ClassVar[ApplicationCommandType]
    __original_kwargs__: Dict[str, Any]
    cog: ClassVar[Optional[CogT]] = None

    _id: ClassVar[str]
    name: ClassVar[str]
    guild_ids: ClassVar[List[int]]

    _before_invoke: ClassVar[Hook]
    _after_invoke: ClassVar[Hook]
    checks: ClassVar[List[Check]]
    _callback: ClassVar[ApplicationCallback]

    # Error/checks handler, etc.
    on_error: Error

    def __new__(cls: Type[AppCommandT], *args: Any, **kwargs: Any) -> AppCommandT:
        self = super().__new__(cls)
        self.__original_kwargs__ = kwargs
        self.checks = []

        return self

    def __repr__(self):
        return f"<discord.ext.app.{self.__class__.__name__} name={self.name}>"

    def __eq__(self, other: AppCommandT):
        return (
            isinstance(other, ApplicationCommand)
            and self.name == other.name
            and self.type == other.type
        )

    @property
    def id(self) -> Optional[str]:
        return getattr(self, '_id', None)

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def callback(self) -> ApplicationCallback:
        return self._callback

    @callback.setter
    def callback(self, function: ApplicationCallback):
        self._callback = function
        self.params = get_signature_parameters(function)

    @property
    def id(self) -> Optional[str]:
        """:class:`Optional[str]`: The application ID."""
        return getattr(self, '_id', None)

    @id.setter
    def id(self, value: Optional[str]):
        self._id = value

    @property
    def qualified_name(self):
        """:class:`str`: The application qualified name."""
        return self.name

    async def __call__(self, ctx: ApplicationContext, *args: Any, **kwargs: Any):
        """|coro|

        Calls the command's callback.
        This method bypasses all checks that a command has and does not
        convert the arguments beforehand, so take care to pass the correct
        arguments in.
        Parameters
        ----------
        ctx: :class:`.ApplicationContext`
            The context of the command.
        """
        if self.cog is not None:
            return await self.callback(self.cog, ctx, *args, **kwargs)
        else:
            return await self.callback(ctx, *args, **kwargs)

    async def _parse_arguments(self, ctx: ApplicationContext):
        """|coro|

        Parse the argument and such. Implement later on child
        """
        raise NotImplementedError

    async def prepare(self, ctx: ApplicationContext):
        # Bind
        ctx.command = self

        # Handle checks
        if not await self.can_run(ctx):
            raise ApplicationCheckFailure(f'The check functions for command {self.qualified_name} failed.')

        # TODO: Check cooldowns
        # -- Probably reimplement how discord.ext.commands.cooldown works

        await self._parse_arguments(ctx)
        await self.call_before_hooks(ctx)

    def error(self, coro: ErrorT) -> ErrorT:
        """A decorator that registers a coroutine as a local error handler.

        A local error handler is an :func:`.on_application_command_error` event limited to
        a single command. However, the :func:`.on_application_command_error` is still
        invoked afterwards as the catch-all.

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register as the local error handler.

        Raises
        -------
        TypeError
            The coroutine passed is not actually a coroutine.
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('The error handler must be a coroutine.')

        self.on_error = coro
        return coro

    def has_error_handler(self) -> bool:
        """:class:`bool`: Checks whether the command has an error handler registered.
        """
        return hasattr(self, 'on_error')

    def add_check(self, func: Check) -> None:
        """Adds a check to the command.

        This is the non-decorator interface to :func:`.check`.

        Parameters
        -----------
        func
            The function that will be used as a check.
        """

        self.checks.append(func)

    def remove_check(self, func: Check) -> None:
        """Removes a check from the command.

        This function is idempotent and will not raise an exception
        if the function is not in the command's checks.

        Parameters
        -----------
        func
            The function to remove from the checks.
        """

        try:
            self.checks.remove(func)
        except ValueError:
            pass

    def before_invoke(self, coro: HookT) -> HookT:
        """A decorator that registers a coroutine as a pre-invoke hook.

        A pre-invoke hook is called directly before the command is
        called. This makes it a useful function to set up database
        connections or any type of set up required.

        This pre-invoke hook takes a sole parameter, a :class:`.ApplicationContext`.

        See :meth:`.Bot.before_invoke` for more info.

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register as the pre-invoke hook.

        Raises
        -------
        TypeError
            The coroutine passed is not actually a coroutine.
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('The pre-invoke hook must be a coroutine.')

        self._before_invoke = coro
        return coro

    def after_invoke(self, coro: HookT) -> HookT:
        """A decorator that registers a coroutine as a post-invoke hook.

        A post-invoke hook is called directly after the command is
        called. This makes it a useful function to clean-up database
        connections or any type of clean up required.

        This post-invoke hook takes a sole parameter, a :class:`.ApplicationContext`.

        See :meth:`.Bot.after_invoke` for more info.

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register as the post-invoke hook.

        Raises
        -------
        TypeError
            The coroutine passed is not actually a coroutine.
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('The post-invoke hook must be a coroutine.')

        self._after_invoke = coro
        return coro

    @property
    def cog_name(self) -> Optional[str]:
        """Optional[:class:`str`]: The name of the cog this command belongs to, if any."""
        return type(self.cog).__cog_name__ if self.cog is not None else None

    def _is_typing_optional(self, annotation: Union[T, Optional[T]]) -> TypeGuard[Optional[T]]:
        return getattr(annotation, '__origin__', None) is Union and type(None) in annotation.__args__  # type: ignore

    @classmethod
    def _get_overridden_method(cls, method: FuncT) -> Optional[FuncT]:
        """Return None if the method is not overridden. Otherwise returns the overridden method."""
        return getattr(method.__func__, '__cog_special_method__', method)

    async def dispatch_error(self, ctx: ApplicationContext, error: Exception) -> None:
        ctx.command_failed = True
        cog = self.cog
        try:
            coro = self.on_error
        except AttributeError:
            pass
        else:
            injected = wrap_callback(coro)
            if cog is not None:
                await injected(cog, ctx, error)
            else:
                await injected(ctx, error)

        try:
            if cog is not None:
                local = self._get_overridden_method(cog.cog_command_error)
                if local is not None:
                    wrapped = wrap_callback(local)
                    await wrapped(ctx, error)
        finally:
            ctx.bot.dispatch('application_error', ctx, error)

    async def call_before_hooks(self, ctx: ApplicationContext) -> None:
        # now that we're done preparing we can call the pre-command hooks
        # first, call the command local hook:
        cog = self.cog
        if self._before_invoke is not None:
            # should be cog if @commands.before_invoke is used
            instance = getattr(self._before_invoke, '__self__', cog)
            # __self__ only exists for methods, not functions
            # however, if @command.before_invoke is used, it will be a function
            if instance:
                await self._before_invoke(instance, ctx)  # type: ignore
            else:
                await self._before_invoke(ctx)  # type: ignore

        # call the cog local hook if applicable:
        if cog is not None:
            hook = self._get_overridden_method(cog.cog_before_invoke)
            if hook is not None:
                await hook(ctx)

        # call the bot global hook if necessary
        hook = ctx.bot._before_invoke
        if hook is not None:
            await hook(ctx)

    async def call_after_hooks(self, ctx: ApplicationContext) -> None:
        cog = self.cog
        if self._after_invoke is not None:
            instance = getattr(self._after_invoke, '__self__', cog)
            if instance:
                await self._after_invoke(instance, ctx)  # type: ignore
            else:
                await self._after_invoke(ctx)  # type: ignore

        # call the cog local hook if applicable:
        if cog is not None:
            hook = self._get_overridden_method(cog.cog_after_invoke)
            if hook is not None:
                await hook(ctx)

        hook = ctx.bot._after_invoke
        if hook is not None:
            await hook(ctx)

    async def invoke(self, ctx: ApplicationContext) -> None:
        """|coro|

        Execute or invoke the function callback of the app command.

        Parameters
        -----------
        ctx: :class:`.ApplicationContext`
            The invocation context.

        Raises
        -------
        ApplicationCommandInvokeError
            An error occurred while invoking the command.
        """

        await self.prepare(ctx)

        injected = hooked_wrapped_callback(self, ctx, self.callback)
        await injected(*ctx.args, **ctx.kwargs)

    async def reinvoke(self, ctx: ApplicationContext, *, call_hooks: bool = False):
        """|coro|

        Execute again or reinvoke the function callback of the app command.
        This will perform a similar action to :meth:`.Bot.invoke` except
        you can set if you want to invoke hooks or not.

        This will also bypass the concurrency checks and cooldown check.

        Parameters
        -----------
        ctx: :class:`.ApplicationContext`
            The invocation context.
        call_hooks: :class:`bool`
            Should we call the before_hooks and after_hooks or not.

        Raises
        -------
        ApplicationCommandInvokeError
            An error occurred while invoking the command.
        """
        ctx.command = self
        await self._parse_arguments(ctx)
        if call_hooks:
            await self.call_before_hooks(ctx)

        try:
            await self.callback(*ctx.args, **ctx.kwargs)
        except:
            ctx.command_failed = True
            raise
        finally:
            if call_hooks:
                await self.call_after_hooks(ctx)

    def _ensure_assignment_on_copy(self, other: AppCommandT) -> AppCommandT:
        other._before_invoke = self._before_invoke
        other._after_invoke = self._after_invoke
        if self.checks != other.checks:
            other.checks = self.checks.copy()

        try:
            other.on_error = self.on_error
        except AttributeError:
            pass
        return other

    def copy(self: AppCommandT) -> AppCommandT:
        """Creates a copy of this app command.

        Returns
        --------
        :class:`ApplicationCommand`
            A new instance of this app command.
        """
        ret = self.__class__(self.callback, **self.__original_kwargs__)
        return self._ensure_assignment_on_copy(ret)

    async def can_run(self, ctx: ApplicationContext) -> bool:
        """|coro|

        Checks if the command can be executed by checking all the predicates
        inside the :attr:`~Command.checks` attribute. This also checks whether the
        command is disabled.

        Parameters
        -----------
        ctx: :class:`.ApplicationContext`
            The ctx of the command currently being invoked.

        Raises
        -------
        :class:`CommandError`
            Any command error that was raised during a check call will be propagated
            by this function.

        Returns
        --------
        :class:`bool`
            A boolean indicating if the command can be invoked.
        """

        original = ctx.command
        ctx.command = self

        try:
            if not await ctx.bot.can_run(ctx):
                raise ApplicationCheckFailure(f'The global check functions for command {self.qualified_name} failed.')

            cog = self.cog
            if cog is not None:
                local_check = self._get_overridden_method(cog.cog_check)
                if local_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_check, ctx)
                    if not ret:
                        return False

            predicates = self.checks
            if not predicates:
                return True

            return await discord.utils.async_all(predicate(ctx) for predicate in predicates)  # type: ignore
        finally:
            ctx.command = original

    def to_dict(self):
        """:class:`dict`: A discord API friendly dictionary that can be submitted to the API.
        """
        _DEFAULT = "No description provided"
        options: Optional[List[Option]] = getattr(self, 'options', None)
        base_return = {
            'name': self.name,
            'type': self.type.value,
        }
        if options:
            base_return['options'] = [o.to_dict() for o in options]
        _desc_fallback = _DEFAULT if self.type == ApplicationCommandType.slash else ""
        description = getattr(self, "description", _desc_fallback)
        base_return['description'] = description
        return base_return


class Option:
    def __init__(
        self, input_type: Type[Any], /, description: str = None, **kwargs,
    ):
        self.name: Optional[str] = kwargs.pop('name', None)
        self.description = description or "No description provided"
        self.input_type = SlashCommandOptionType.from_datatype(input_type)
        self.required: bool = kwargs.pop('required', True)
        self.choices: List[OptionChoice] = [
            o if isinstance(o, OptionChoice) else OptionChoice(o)
            for o in kwargs.pop('choices', [])
        ]
        self.default: Optional[Any] = kwargs.pop('default', None)

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'type': self.input_type.value,
            'required': self.required,
            'choices': [c.to_dict() for c in self.choices],
            'default': self.default,
        }

    def __repr__(self):
        return f'<discord.ext.app.Option name={self.name}>'

class OptionChoice:
    def __init__(self, name: str, value: Optional[Union[str, int, float]] = None):
        self.name = name
        self.value = value or name

    def to_dict(self):
        return {'name': self.name, 'value': self.value}


class SlashCommand(ApplicationCommand):
    type = ApplicationCommandType.slash
    sub_type = SlashCommandOptionType.sub_command
    parent: SlashCommand = None

    description: ClassVar[str]
    options: List[Option]

    def __new__(cls: Type[SlashCommand], *args, **kwargs) -> SlashCommand:
        self = super().__new__(cls)
        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(self, callback: ApplicationCallback, *args, **kwargs) -> None:
        if not asyncio.iscoroutinefunction(callback):
            raise TypeError('Callback must be a coroutine.')

        self._callback = callback
        self.guild_ids: Optional[List[int]] = kwargs.get("guild_ids", None)
        fn_name = kwargs.get("name") or callback.__name__
        self.name = fn_name

        description = kwargs.get('description') or (
            inspect.cleandoc(callback.__doc__).splitlines()[0]
            if callback.__doc__ is not None
            else "No description provided"
        )
        self.description = description

        self.params = get_signature_parameters(callback)
        self.options: List[Option] = self.parse_options()

        self._children: Dict[str, SlashCommand] = {}

        try:
            checks = callback.__commands_checks__
        except AttributeError:
            checks = kwargs.get('checks', [])

        self.checks: List[Check] = checks

        self.cog: Optional[CogT] = None
        self._before_invoke: Optional[Hook] = None
        try:
            before_invoke = callback.__before_invoke__
        except AttributeError:
            pass
        else:
            self.before_invoke(before_invoke)

        self._after_invoke: Optional[Hook] = None
        try:
            after_invoke = callback.__after_invoke__
        except AttributeError:
            pass
        else:
            self.after_invoke(after_invoke)

    def is_match(self, other: "SlashCommand"):
        return self.name == other.name and self.sub_type == other.sub_type

    def parse_options(self) -> List[Option]:
        _NO_DESC = "No description provided"
        options = []
        params = self.params

        if list(params.items())[0][0] == 'self':
            temp = list(params.items())
            temp.pop(0)
            params = OrderedDict(temp)

        params = iter(params.items())

        # process the ctx parameter
        try:
            next(params)
        except StopIteration:
            raise ClientException(
                f'Callback for {self.name} command is missing "ctx" parameter.'
            )

        # Get the slash option from class, if missing just return dict.
        slash_options: Dict[str, Option] = getattr(self.callback, '__slash_options__', getattr(self, '__slash_options__', {}))

        for name, param in params:
            option = param.annotation
            if option == inspect.Parameter.empty:
                option = str

            if self._is_typing_optional(param):
                option = Option(
                    option.__args__[0], description=_NO_DESC, required=False
                )

            option = slash_options.get(name, option)

            if not isinstance(option, Option):
                option = Option(option, description=_NO_DESC)
                if param.default != inspect.Parameter.empty:
                    option.required = False

            option.default = option.default or param.default
            if option.default == inspect.Parameter.empty:
                option.default = None

            if option.name is None:
                option.name = name
            options.append(option)
        return options

    def __eq__(self, other: "SlashCommand") -> bool:
        return (
            isinstance(other, SlashCommand)
            and other.name == self.name
        )

    async def _parse_arguments(self, ctx: ApplicationContext):
        _INVALID_TYPE = [SlashCommandOptionType.sub_command.value, SlashCommandOptionType.sub_command_group.value]
        args = [ctx] if self.cog is None else [self.cog, ctx]
        kwargs = {}

        for arg in ctx.interaction.data.get('options', []):
            # Skip if type is sub_command or sub_command_group
            if arg['type'] in _INVALID_TYPE:
                continue
            op = discord.utils.find(lambda o: o.name == arg['name'], self.options)
            arg = arg['value']

            if (
                SlashCommandOptionType.user.value
                <= op.input_type.value
                <= SlashCommandOptionType.role.value
            ):
                name = 'member' if op.input_type == 'user' else op.input_type.name
                arg = await discord.utils.get_or_fetch(ctx.guild, name, int(arg), default=int(arg))
            elif op.input_type == SlashCommandOptionType.mentionable:
                arg_id = int(arg)
                arg = await discord.utils.get_or_fetch(ctx.guild, 'member', arg_id)
                if arg is None:
                    arg = ctx.guild.get_role(arg_id) or arg_id
            if arg is None and op.default is not None:
                arg = op.default
            kwargs[op.name] = arg

        ctx.args = args
        ctx.kwargs = kwargs

    @property
    def children(self):
        """Dict[:class:`str`, :class:`SlashCommand`]: A list of children"""
        return self._children

    def has_parent(self):
        """:class:`bool`: Check if the command have parent or not.
        """
        return hasattr(self, 'parent') and self.parent is not None

    async def _invoke_children(self, ctx: ApplicationContext):
        """|coro|

        Execute all the children of the slash group command.

        Parameters
        -----------
        ctx: :class:`.ApplicationContext`
            The invocation context.

        Raises
        -------
        ApplicationCommandInvokeError
            An error occurred while invoking the command.
        """
        if not self._children:
            # Exit fast if there's no child
            return
        data = ctx.interaction.data
        options = data.get('options', [])
        if not options:
            return

        first_children = options[0]
        if not first_children:
            return
        sub_command: Optional[SlashCommand] = None
        if first_children.get('type') == 2:
            sub_command = self._children.get(first_children.get('name'))
            first_child_opts = first_children.get('options', [])
            try:
                ff_opt = first_child_opts[0]
                if ff_opt and ff_opt.get('type') == 1 and sub_command is not None:
                    sub_command = sub_command.children.get(ff_opt.get('name'))
            except IndexError:
                pass
        else:
            sub_command = self._children.get(first_children.get('name'))

        if sub_command is not None:
            ctx.invoked_subcommand = sub_command
            try:
                await sub_command.invoke(ctx)
            except Exception as err:
                sub_command.dispatch_error(ctx, err)
                ctx.command_failed = True
                raise err

    async def invoke(self, ctx: ApplicationContext) -> None:
        await super().invoke(ctx)
        await self._invoke_children(ctx)

    def add_command(self, command: "SlashCommand"):
        """Adds a :class:`.SlashCommand` into the internal list of commands.

        This is usually not called, instead the :meth:`~.ApplicationCommand.command` or
        :meth:`~.ApplicationCommand.group` shortcut decorators are used instead.

        .. versionchanged:: 1.4
             Raise :exc:`.CommandRegistrationError` instead of generic :exc:`.ClientException`

        Parameters
        -----------
        command: :class:`Command`
            The command to add.

        Raises
        -------
        :exc:`.ApplicationRegistrationError`
            If the command or its alias is already registered by different command.
        :exc:`.ApplicationRegistrationMaxDepthError`
            If the command parent already reach the maximum depth of 2 nested child.
        :exc:`.ApplicationRegistrationExistingParentOptions`
            If the parent command contains options other than `sub_command` or `sub_command_group`.
        TypeError
            If the command passed is not a subclass of :class:`.SlashCommand`.
        """

        if command.type != (ApplicationCommandType.slash or ApplicationCommandType.slash_group):
            raise TypeError('The command passed must be a subclass of SlashCommand')

        if command.name in self._children:
            raise ApplicationRegistrationError(command.name)

        if self.has_parent() and self.sub_type != SlashCommandOptionType.sub_command_group:
                raise ApplicationRegistrationMaxDepthError(command.name)
        for opts in self.options:
            # Check if the option contains anything beside sub_command or sub_command_group
            if opts.input_type != (SlashCommandOptionType.sub_command or SlashCommandOptionType.sub_command_group):
                raise ApplicationRegistrationExistingParentOptions(command.name, opts)

        self._children[command.name] = command

    @property
    def commands(self) -> Set[SlashCommand]:
        """Set[:class:`.SlashCommand`]: A unique set of commands without aliases that are registered."""
        return set(self._children.values())

    def walk_commands(self) -> Generator[SlashCommand, None, None]:
        """An iterator that recursively walks through all commands and subcommands.

        Yields
        ------
        :class:`SlashCommand`:
            A command or group from the internal list of commands.
        """
        yield self
        for command in self.commands:
            if command.sub_type == SlashCommandOptionType.sub_command_group:
                yield command.walk_commands()
            else:
                yield command

    def to_dict(self):
        dict_res = super().to_dict()
        if self._children:
            child_res = [child.to_dict() for child in self._children.values()]
            if 'options' not in dict_res:
                dict_res['options'] = []
            dict_res['options'].extend(child_res)
        if not self.has_parent() and 'type' in dict_res:
            del dict_res['type']
        elif self.has_parent():
            dict_res['type'] = self.sub_type.value
        return dict_res

    # Decorator
    @overload
    def command(
        self,
        name: str = ...,
        description: str = ...,
        *args: Any,
        **kwargs: Any,
    ) -> DecoApp[SlashCommand]:
        ...

    def command(self, *args, **kwargs):
        """A decorator that would add a new subcommand to the parent command.

        Returns
        --------
        Callable[..., :class:`.SlashCommand`]
            A decorator that converts the provided method into a :class:`.SlashCommand`, adds it to the bot, then returns it.
        """

        def decorator(func: Callable[Concatenate[ContextT, P], Coro[Any]]) -> SlashCommand:
            # Remove guild_ids
            kwargs.pop('guild_ids', None)
            result = SlashCommand(func, *args, **kwargs)
            # Set parent
            setattr(result, 'parent', self)
            self.add_command(result)
            return result

        return decorator

    @overload
    def group(
        self,
        name: str = ...,
        description: str = ...,
        *args: Any,
        **kwargs: Any,
    ) -> DecoApp[SlashCommand]:
        ...

    def group(self, *args, **kwargs):
        """A decorator that would add a new subcommand group to the parent command.

        Returns
        --------
        Callable[..., :class:`.SlashCommand`]
            A decorator that converts the provided method into a :class:`.SlashCommand`, adds it to the bot, then returns it.
        """

        def decorator(func: Callable[Concatenate[ContextT, P], Coro[Any]]) -> SlashCommand:
            kwargs.setdefault('parent', self)
            # Remove guild_ids
            kwargs.pop('guild_ids', None)
            result = SlashCommand(func, *args, **kwargs)
            # Set parent
            setattr(result, 'parent', self)
            # Override the sub_type
            result.sub_type = SlashCommandOptionType.sub_command_group
            self.add_command(result)
            return result

        return decorator


class ContextMenuApplication(ApplicationCommand):
    def __new__(cls: Type[ContextMenuApplication], *args, **kwargs) -> ContextMenuApplication:
        self = super().__new__(cls)
        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(self, callback: ApplicationCallback, *args, **kwargs) -> None:
        self._callback = callback
        self.guild_ids: Optional[List[int]] = kwargs.get("guild_ids", None)

        fn_name = kwargs.get("name") or callback.__name__
        self.name = fn_name

        self.params = get_signature_parameters(callback)

        try:
            checks = callback.__commands_checks__
        except AttributeError:
            checks = kwargs.get('checks', [])

        self.checks: List[Check] = checks

        self.cog: Optional[CogT] = None
        self._before_invoke: Optional[Hook] = None
        try:
            before_invoke = callback.__before_invoke__
        except AttributeError:
            pass
        else:
            self.before_invoke(before_invoke)

        self._after_invoke: Optional[Hook] = None
        try:
            after_invoke = callback.__after_invoke__
        except AttributeError:
            pass
        else:
            self.after_invoke(after_invoke)

    def walk_commands(self) -> Generator[ContextMenuApplication, None, None]:
        """An iterator that recursively walks through all commands and subcommands.

        Yields
        ------
        :class:`.ContextMenuApplication`:
            A command or group from the internal list of commands.
        """
        yield self

    async def _parse_arguments(self, ctx: ApplicationContext):
        args = [ctx] if self.cog is None else [self.cog, ctx]
        ctx.args = args
        ctx.kwargs = {}

        resolved = ctx.interaction.data.get('resolved')
        if resolved is None:
            ctx.args.append(MISSING)
            return

        if self.type == ApplicationCommandType.user:
            if "members" in resolved:
                members = resolved['members']
                for member_id, member_data in members.items():
                    member_data["id"] = int(member_id)
                    member = member_data
                users = resolved['users']
                for user_id, user_data in users.items():
                    user_data["id"] = int(user_id)
                    user = user_data
                member["user"] = user
                ctx.args.append(
                    Member(
                        data=member,
                        guild=ctx.interaction._state._get_guild(ctx.interaction.guild_id),
                        state=ctx.interaction._state,
                    )
                )
            else:
                users = resolved.users
                for user_id, user_data in users.items():
                    user_data["id"] = int(user_id)
                    user = user_data
                ctx.args.append(User(data=user, state=ctx.interaction._state))
        elif self.type == ApplicationCommandType.message:
            messages = resolved['messages']
            for msg_id, msg_data in messages.items():
                msg_data["id"] = int(msg_id)
                msg = msg_data
            channel = ctx.interaction._state.get_channel(int(msg["channel_id"]))
            if channel is None:
                data = await ctx.interaction._state.http.start_private_message(
                    int(messages["author"]["id"])
                )
                channel = ctx.interaction._state.add_dm_channel(data)

            ctx.args.append(
                Message(state=ctx.interaction._state, channel=channel, data=msg)
            )


class UserCommand(ContextMenuApplication):
    type = ApplicationCommandType.user

    def __new__(cls: Type[UserCommand], *args, **kwargs) -> UserCommand:
        self = super().__new__(cls)
        self.__original_kwargs__ = kwargs.copy()
        return self


class MessageCommand(ContextMenuApplication):
    type = ApplicationCommandType.message

    def __new__(cls: Type[MessageCommand], *args, **kwargs) -> MessageCommand:
        self = super().__new__(cls)
        self.__original_kwargs__ = kwargs.copy()
        return self


@overload
def option(
    name: str,
    type: AcceptedInputType,
    *,
    description: str = None,
    required: bool = True,
    choices: List[Union[OptionChoice, str]] = [],
    default: Optional[Any] = None,
) -> Option:
    ...

def option(name, type=None, **kwargs):
    """A decorator that can be used instead of typehinting Option"""
    def decor(func: ApplicationCallback):
        nonlocal type
        type = type or func.__annotations__.get(name, str)
        if not hasattr(func, '__slash_options__'):
            func.__slash_options__ = {}
        func.__slash_options__[name] = Option(type, **kwargs)
        return func
    return decor

@overload
def application_command(
    cls: Type[AppCommandT] = SlashCommand,
    *,
    name: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[AppCommandT]:
    ...

@overload
def application_command(
    cls: Type[AppCommandT] = SlashCommand,
    *,
    name: Optional[str] = MISSING,
    description: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[AppCommandT]:
    ...

def application_command(cls=SlashCommand, **attrs):
    """A decorator that transforms a function into an :class:`.ApplicationCommand`. More specifically,
    usually one of :class:`.SlashCommand`, :class:`.UserCommand`, or :class:`.MessageCommand`. The exact class
    depends on the ``cls`` parameter.

    By default the ``description`` attribute is received automatically from the
    docstring of the function and is cleaned up with the use of
    ``inspect.cleandoc``. If the docstring is ``bytes``, then it is decoded
    into :class:`str` using utf-8 encoding.

    The ``name`` attribute also defaults to the function name unchanged.

    .. versionadded:: 2.0

    Parameters
    -----------
    cls: :class:`.ApplicationCommand`
        The class to construct with. By default this is :class:`.SlashCommand`.
        You usually do not change this.
    attrs
        Keyword arguments to pass into the construction of the class denoted
        by ``cls``.

    Raises
    -------
    TypeError
        If the function is not a coroutine or is already a command.
    """

    def decorator(func: Callable) -> cls:
        if isinstance(func, ApplicationCommand):
            func = func.callback
        elif not callable(func):
            raise TypeError(
                "func needs to be a callable or a subclass of ApplicationCommand."
            )
        return cls(func, **attrs)

    return decorator

@overload
def slash_command(
    *,
    name: Optional[str] = MISSING,
    description: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[SlashCommand]:
    ...

def slash_command(**kwargs):
    """Decorator for slash commands that invokes :func:`application_command`.

    .. versionadded:: 2.0

    Returns
    --------
    Callable[..., :class:`SlashCommand`]
        A decorator that converts the provided method into a :class:`.SlashCommand`.
    """
    return application_command(cls=SlashCommand, **kwargs)

@overload
def user_command(
    *,
    name: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[UserCommand]:
    ...

def user_command(**kwargs):
    """Decorator for user commands that invokes :func:`application_command`.

    .. versionadded:: 2.0

    Returns
    --------
    Callable[..., :class:`UserCommand`]
        A decorator that converts the provided method into a :class:`.UserCommand`.
    """
    return application_command(cls=UserCommand, **kwargs)

@overload
def message_command(
    *,
    name: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[MessageCommand]:
    ...

def message_command(**kwargs):
    """Decorator for message commands that invokes :func:`application_command`.

    .. versionadded:: 2.0

    Returns
    --------
    Callable[..., :class:`MessageCommand`]
        A decorator that converts the provided method into a :class:`.MessageCommand`.
    """
    return application_command(cls=MessageCommand, **kwargs)

@overload
def command(
    *,
    cls: Type[AppCommandT] = SlashCommand,
    name: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[AppCommandT]:
    ...

@overload
def command(
    *,
    cls: Type[AppCommandT] = SlashCommand,
    name: Optional[str] = MISSING,
    description: Optional[str] = MISSING,
    guild_ids: Optional[List[int]] = MISSING,
    checks: Optional[List[Check]] = MISSING,
) -> DecoApp[AppCommandT]:
    ...

def command(**kwargs):
    """This is an alias for :meth:`application_command`.

    .. versionadded:: 2.0

    Returns
    --------
    Callable[..., :class:`ApplicationCommand`]
        A decorator that converts the provided method into an :class:`.ApplicationCommand`.
    """
    return application_command(**kwargs)


# check decorators

def check(predicate: Check) -> Callable[[T], T]:
    r"""A decorator that adds a check to the :class:`.ApplicationCommand` or its
    subclasses. These checks could be accessed via :attr:`.ApplicationCommand.checks`.

    These checks should be predicates that take in a single parameter taking
    a :class:`.Context`. If the check returns a ``False``\-like value then
    during invocation a :exc:`.ApplicationCheckFailure` exception is raised and sent to
    the :func:`.on_command_error` event.

    If an exception should be thrown in the predicate then it should be a
    subclass of :exc:`.ApplicationCommandError`. Any exception not subclassed from it
    will be propagated while those subclassed will be sent to
    :func:`.on_command_error`.

    A special attribute named ``predicate`` is bound to the value
    returned by this decorator to retrieve the predicate passed to the
    decorator. This allows the following introspection and chaining to be done:

    .. code-block:: python3

        def owner_or_permissions(**perms):
            original = commands.has_permissions(**perms).predicate
            async def extended_check(ctx):
                if ctx.guild is None:
                    return False
                return ctx.guild.owner_id == ctx.author.id or await original(ctx)
            return commands.check(extended_check)

    .. note::

        The function returned by ``predicate`` is **always** a coroutine,
        even if the original function was not a coroutine.

    .. versionchanged:: 1.3
        The ``predicate`` attribute was added.

    Examples
    ---------

    Creating a basic check to see if the command invoker is you.

    .. code-block:: python3

        def check_if_it_is_me(ctx):
            return ctx.message.author.id == 85309593344815104

        @bot.command()
        @commands.check(check_if_it_is_me)
        async def only_for_me(ctx):
            await ctx.send('I know you!')

    Transforming common checks into its own decorator:

    .. code-block:: python3

        def is_me():
            def predicate(ctx):
                return ctx.message.author.id == 85309593344815104
            return commands.check(predicate)

        @bot.command()
        @is_me()
        async def only_me(ctx):
            await ctx.send('Only you!')

    Parameters
    -----------
    predicate: Callable[[:class:`ApplicationContext`], :class:`bool`]
        The predicate to check if the command should be invoked.
    """

    def decorator(func: Union[ApplicationCommand, ApplicationCallback]) -> Union[ApplicationCommand, ApplicationCallback]:
        if isinstance(func, ApplicationCommand):
            func.checks.append(predicate)
        else:
            if not hasattr(func, '__commands_checks__'):
                func.__commands_checks__ = []
            func.__commands_checks__.append(predicate)

        return func

    if inspect.iscoroutinefunction(predicate):
        decorator.predicate = predicate
    else:
        @functools.wraps(predicate)
        async def wrapper(ctx):
            return predicate(ctx)
        decorator.predicate = wrapper

    return decorator

def check_any(*checks: Check) -> Callable[[T], T]:
    r"""A :func:`check` that is added that checks if any of the checks passed
    will pass, i.e. using logical OR.

    If all checks fail then :exc:`.CheckAnyFailure` is raised to signal the failure.
    It inherits from :exc:`.ApplicationCheckFailure`.

    .. note::

        The ``predicate`` attribute for this function **is** a coroutine.

    .. versionadded:: 2.0

    Parameters
    ------------
    \*checks: Callable[[:class:`ApplicationContext`], :class:`bool`]
        An argument list of checks that have been decorated with
        the :func:`check` decorator.

    Raises
    -------
    TypeError
        A check passed has not been decorated with the :func:`check`
        decorator.

    Examples
    ---------

    Creating a basic check to see if it's the bot owner or
    the server owner:

    .. code-block:: python3

        def is_guild_owner():
            def predicate(ctx):
                return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
            return commands.check(predicate)

        @bot.command()
        @commands.check_any(commands.is_owner(), is_guild_owner())
        async def only_for_owners(ctx):
            await ctx.send('Hello mister owner!')
    """

    unwrapped = []
    for wrapped in checks:
        try:
            pred = wrapped.predicate
        except AttributeError:
            raise TypeError(f'{wrapped!r} must be wrapped by commands.check decorator') from None
        else:
            unwrapped.append(pred)

    async def predicate(ctx: ApplicationContext) -> bool:
        errors = []
        for func in unwrapped:
            try:
                value = await func(ctx)
            except ApplicationCheckFailure as e:
                errors.append(e)
            else:
                if value:
                    return True
        # if we're here, all checks failed
        raise ApplicationCheckAnyFailure(unwrapped, errors)

    return check(predicate)

def has_role(item: Union[int, str]) -> Callable[[T], T]:
    """A :func:`.check` that is added that checks if the member invoking the
    command has the role specified via the name or ID specified.

    If a string is specified, you must give the exact name of the role, including
    caps and spelling.

    If an integer is specified, you must give the exact snowflake ID of the role.

    If the message is invoked in a private message context then the check will
    return ``False``.

    This check raises one of two special exceptions, :exc:`.ApplicationMissingRole` if the user
    is missing a role, or :exc:`.ApplicationNoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.ApplicationCheckFailure`.

    Parameters
    -----------
    item: Union[:class:`int`, :class:`str`]
        The name or ID of the role to check.
    """

    def predicate(ctx: ApplicationContext) -> bool:
        if ctx.guild is None:
            raise ApplicationNoPrivateMessage

        # ctx.guild is None doesn't narrow ctx.author to Member
        if isinstance(item, int):
            role = discord.utils.get(ctx.author.roles, id=item)  # type: ignore
        else:
            role = discord.utils.get(ctx.author.roles, name=item)  # type: ignore
        if role is None:
            raise ApplicationMissingRole(item)
        return True

    return check(predicate)

def bot_has_role(item: int) -> Callable[[T], T]:
    """Similar to :func:`.has_role` except checks if the bot itself has the
    role.

    This check raises one of two special exceptions, :exc:`.ApplicationBotMissingRole` if the bot
    is missing the role, or :exc:`.ApplicationNoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.CheckFailure`.
    """

    def predicate(ctx: ApplicationContext):
        if ctx.guild is None:
            raise ApplicationNoPrivateMessage

        me = ctx.me
        if isinstance(item, int):
            role = discord.utils.get(me.roles, id=item)
        else:
            role = discord.utils.get(me.roles, name=item)
        if role is None:
            raise ApplicationBotMissingRole(item)
        return True
    return check(predicate)

def has_any_role(*items: Union[int, str]) -> Callable[[T], T]:
    r"""A :func:`.check` that is added that checks if the member invoking the
    command has **any** of the roles specified. This means that if they have
    one out of the three roles specified, then this check will return `True`.

    Similar to :func:`.has_role`\, the names or IDs passed in must be exact.

    This check raises one of two special exceptions, :exc:`.ApplicationMissingAnyRole` if the user
    is missing all roles, or :exc:`.ApplicationNoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.ApplicationCheckFailure`.

        Raise :exc:`.ApplicationMissingAnyRole` or :exc:`.ApplicationNoPrivateMessage`
        instead of generic :exc:`.ApplicationCheckFailure`

    Parameters
    -----------
    items: List[Union[:class:`str`, :class:`int`]]
        An argument list of names or IDs to check that the member has roles wise.

    Example
    --------

    .. code-block:: python3

        @bot.command()
        @commands.has_any_role('Library Devs', 'Moderators', 492212595072434186)
        async def cool(ctx):
            await ctx.send('You are cool indeed')
    """
    def predicate(ctx: ApplicationContext) -> bool:
        if ctx.guild is None:
            raise ApplicationNoPrivateMessage

        # ctx.guild is None doesn't narrow ctx.author to Member
        getter = functools.partial(discord.utils.get, ctx.author.roles)  # type: ignore
        if any(getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None for item in items):
            return True
        raise ApplicationMissingAnyRole(list(items))

    return check(predicate)

def bot_has_any_role(*items: int) -> Callable[[T], T]:
    """Similar to :func:`.has_any_role` except checks if the bot itself has
    any of the roles listed.

    This check raises one of two special exceptions, :exc:`.ApplicationBotMissingAnyRole` if the bot
    is missing all roles, or :exc:`.ApplicationNoPrivateMessage` if it is used in a private message.
    Both inherit from :exc:`.ApplicationCheckFailure`.
    """
    def predicate(ctx: ApplicationContext):
        if ctx.guild is None:
            raise ApplicationNoPrivateMessage

        me = ctx.me
        getter = functools.partial(discord.utils.get, me.roles)
        if any(getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None for item in items):
            return True
        raise ApplicationBotMissingAnyRole(list(items))
    return check(predicate)

def has_permissions(**perms: bool) -> Callable[[T], T]:
    """A :func:`.check` that is added that checks if the member has all of
    the permissions necessary.

    Note that this check operates on the current channel permissions, not the
    guild wide permissions.

    The permissions passed in must be exactly like the properties shown under
    :class:`.discord.Permissions`.

    This check raises a special exception, :exc:`.ApplicationMissingPermissions`
    that is inherited from :exc:`.ApplicationCheckFailure`.

    Parameters
    ------------
    perms
        An argument list of permissions to check for.

    Example
    ---------

    .. code-block:: python3

        @bot.command()
        @commands.has_permissions(manage_messages=True)
        async def test(ctx):
            await ctx.send('You can manage messages.')

    """

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx: ApplicationContext) -> bool:
        ch = ctx.channel
        permissions = ch.permissions_for(ctx.author)  # type: ignore

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise ApplicationMissingPermissions(missing)

    return check(predicate)

def bot_has_permissions(**perms: bool) -> Callable[[T], T]:
    """Similar to :func:`.has_permissions` except checks if the bot itself has
    the permissions listed.

    This check raises a special exception, :exc:`.ApplicationBotMissingPermissions`
    that is inherited from :exc:`.ApplicationCheckFailure`.
    """

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx: ApplicationContext) -> bool:
        guild = ctx.guild
        me = guild.me if guild is not None else ctx.bot.user
        permissions = ctx.channel.permissions_for(me)  # type: ignore

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise ApplicationBotMissingPermissions(missing)

    return check(predicate)

def has_guild_permissions(**perms: bool) -> Callable[[T], T]:
    """Similar to :func:`.has_permissions`, but operates on guild wide
    permissions instead of the current channel permissions.

    If this check is called in a DM context, it will raise an
    exception, :exc:`.ApplicationNoPrivateMessage`.
    """

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx: ApplicationContext) -> bool:
        if not ctx.guild:
            raise ApplicationNoPrivateMessage

        permissions = ctx.author.guild_permissions  # type: ignore
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise ApplicationMissingPermissions(missing)

    return check(predicate)

def bot_has_guild_permissions(**perms: bool) -> Callable[[T], T]:
    """Similar to :func:`.has_guild_permissions`, but checks the bot
    members guild permissions.
    """

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx: ApplicationContext) -> bool:
        if not ctx.guild:
            raise ApplicationNoPrivateMessage

        permissions = ctx.me.guild_permissions  # type: ignore
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise ApplicationBotMissingPermissions(missing)

    return check(predicate)

def dm_only() -> Callable[[T], T]:
    """A :func:`.check` that indicates this command must only be used in a
    DM context. Only private messages are allowed when
    using the command.

    This check raises a special exception, :exc:`.ApplicationPrivateMessageOnly`
    that is inherited from :exc:`.ApplicationCheckFailure`.

    .. versionadded:: 2.0
    """

    def predicate(ctx: ApplicationContext) -> bool:
        if ctx.guild is not None:
            raise ApplicationPrivateMessageOnly
        return True

    return check(predicate)

def guild_only() -> Callable[[T], T]:
    """A :func:`.check` that indicates this command must only be used in a
    guild context only. Basically, no private messages are allowed when
    using the command.

    This check raises a special exception, :exc:`.ApplicationNoPrivateMessage`
    that is inherited from :exc:`.ApplicationCheckFailure`.
    """

    def predicate(ctx: ApplicationContext) -> bool:
        if ctx.guild is None:
            raise ApplicationNoPrivateMessage
        return True

    return check(predicate)

def is_owner() -> Callable[[T], T]:
    """A :func:`.check` that checks if the person invoking this command is the
    owner of the bot.

    This is powered by :meth:`.Bot.is_owner`.

    This check raises a special exception, :exc:`.ApplicationNotOwner` that is derived
    from :exc:`.ApplicationCheckFailure`.
    """

    async def predicate(ctx: ApplicationContext) -> bool:
        if not await ctx.bot.is_owner(ctx.author):
            raise ApplicationNotOwner('You do not own this bot.')
        return True

    return check(predicate)

def is_nsfw() -> Callable[[T], T]:
    """A :func:`.check` that checks if the channel is a NSFW channel.

    This check raises a special exception, :exc:`.ApplicationNSFWChannelRequired`
    that is derived from :exc:`.ApplicationCheckFailure`.

    .. versionchanged:: 2.0

        Raise :exc:`.ApplicationNSFWChannelRequired` instead of generic :exc:`.ApplicationCheckFailure`.
        DM channels will also now pass this check.
    """
    def pred(ctx: ApplicationContext) -> bool:
        ch = ctx.channel
        if ctx.guild is None or (isinstance(ch, (discord.TextChannel, discord.Thread)) and ch.is_nsfw()):
            return True
        raise ApplicationNSFWChannelRequired(ch)  # type: ignore
    return check(pred)

def before_invoke(coro) -> Callable[[T], T]:
    """A decorator that registers a coroutine as a pre-invoke hook.

    This allows you to refer to one before invoke hook for several commands that
    do not have to be within the same cog.

    .. versionadded:: 2.0

    Example
    ---------

    .. code-block:: python3

        async def record_usage(ctx):
            print(ctx.author, 'used', ctx.command, 'at', ctx.message.created_at)

        @bot.command()
        @commands.before_invoke(record_usage)
        async def who(ctx): # Output: <User> used who at <Time>
            await ctx.send('i am a bot')

        class What(commands.Cog):

            @commands.before_invoke(record_usage)
            @commands.command()
            async def when(self, ctx): # Output: <User> used when at <Time>
                await ctx.send(f'and i have existed since {ctx.bot.user.created_at}')

            @commands.command()
            async def where(self, ctx): # Output: <Nothing>
                await ctx.send('on Discord')

            @commands.command()
            async def why(self, ctx): # Output: <Nothing>
                await ctx.send('because someone made me')

        bot.add_cog(What())
    """
    def decorator(func: Union[ApplicationCommand, ApplicationCallback]) -> Union[ApplicationCommand, ApplicationCallback]:
        if isinstance(func, ApplicationCommand):
            func.before_invoke(coro)
        else:
            func.__before_invoke__ = coro
        return func
    return decorator  # type: ignore

def after_invoke(coro) -> Callable[[T], T]:
    """A decorator that registers a coroutine as a post-invoke hook.

    This allows you to refer to one after invoke hook for several commands that
    do not have to be within the same cog.

    .. versionadded:: 2.0
    """
    def decorator(func: Union[ApplicationCommand, ApplicationCallback]) -> Union[ApplicationCommand, ApplicationCallback]:
        if isinstance(func, ApplicationCommand):
            func.after_invoke(coro)
        else:
            func.__after_invoke__ = coro
        return func
    return decorator  # type: ignore
