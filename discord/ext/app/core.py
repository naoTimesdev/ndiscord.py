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
import inspect
from typing_extensions import TypeGuard
from collections import OrderedDict
from discord.ext.commands.cog import Cog
import functools
import discord
from discord.errors import ClientException
from discord.enums import ApplicationCommandType, SlashCommandOptionType
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, Union

from ._types import Coro, Hook, Check, CogT, ApplicationCallback, _BaseApplication, Error
from .errors import *
from .context import ApplicationContext

T = TypeVar('T')
AppCommandT = TypeVar('AppCommandT', bound="ApplicationCommand")
ErrorT = TypeVar('ErrorT', bound="Error")
HookT = TypeVar('HookT', bound="Hook")


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

    _before_invoke: ClassVar[Hook]
    _after_invoke: ClassVar[Hook]
    checks: ClassVar[Check]
    _callback: ClassVar[ApplicationCallback]

    # Error/checks handler, etc.
    on_error: Error

    def __new__(cls: Type[AppCommandT], *args: Any, **kwargs: Any) -> AppCommandT:
        self = super().__new__(cls)
        self.__original_kwargs__ = kwargs

        return self

    def __repr__(self):
        return f"<discord.ext.app.{self.__class__.__name__} name={self.name}>"

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
                local = Cog._get_overridden_method(cog.cog_command_error)
                if local is not None:
                    wrapped = wrap_callback(local)
                    await wrapped(ctx, error)
        finally:
            ctx.bot.dispatch('application_command_error', ctx, error)

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
            hook = Cog._get_overridden_method(cog.cog_before_invoke)
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
            hook = Cog._get_overridden_method(cog.cog_after_invoke)
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
                local_check = Cog._get_overridden_method(cog.cog_check)
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


class Option:
    def __init__(
        self, input_type: Type[Any], /, description: str = None, **kwargs,
    ):
        self.name = Optional[str] = kwargs.pop('name', None)
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
            'input_type': self.input_type.value,
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
        return {
            'name': self.name,
            'value': self.value,
        }


class SlashCommand(ApplicationCommand):
    type = SlashCommandOptionType.value

    description: ClassVar[str]
    options: List[]

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

        for name, param in params:
            option = param.annotation
            if option == inspect.Parameter.empty:
                option = str

            if self._is_typing_optional(param):
                option = Option(
                    option.__args__[0], description=_NO_DESC, required=False
                )

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
        args = [ctx] if self.cog is None else [self.cog, ctx]
        kwargs = {}

        for arg in ctx.interaction.data.get('options', []):
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
            kwargs[op.name] = arg

        ctx.args = args
        ctx.kwargs = kwargs

    def to_dict(self) -> Dict:
        as_dict = {
            'name': self.name,
            'description': self.description,
            'options': [o.to_dict() for o in self.options],
        }
        # TODO: Implement group/subcommand

        return as_dict
