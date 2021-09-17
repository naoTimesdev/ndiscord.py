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

from inspect import Parameter
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Union
from discord.errors import ClientException, DiscordException

if TYPE_CHECKING:
    from . import ApplicationContext, Option

    from discord.abc import GuildChannel
    from discord.threads import Thread
    from discord.types.snowflake import Snowflake, SnowflakeList

__all__ = (
    'ApplicationCommandError',
    'ApplicationCheckFailure',
    'ApplicationCommandInvokeError',
    'ApplicationRegistrationError',
    'ApplicationRegistrationMaxDepthError',
    'ApplicationRegistrationExistingParentOptions',

    'ApplicationUserInputError',
    'ApplicationMissingRequiredArgument',
    'ApplicationTooManyArguments',
    'ApplicationBadArgument',
    'ApplicationMemberNotFound',
    'ApplicationUserNotFound',
    'ApplicationMentionableNotFound',
    'ApplicationCommandOnCooldown',

    'ApplicationCheckAnyFailure',
    'ApplicationPrivateMessageOnly',
    'ApplicationNoPrivateMessage',
    'ApplicationMissingRole',
    'ApplicationBotMissingRole',
    'ApplicationMissingAnyRole',
    'ApplicationBotMissingAnyRole',
    'ApplicationMissingPermissions',
    'ApplicationBotMissingPermissions',
    'ApplicationNSFWChannelRequired',
    'ApplicationNotOwner',
)

class ApplicationCommandError(DiscordException):
    r"""The base exception type for all command related errors.

    This inherits from :exc:`discord.DiscordException`.

    This exception and exceptions inherited from it are handled
    in a special way as they are caught and passed into a special event
    from :class:`.Bot`\, :func:`.on_application_error`.
    """
    pass

class ApplicationCheckFailure(ApplicationCommandError):
    r"""Exception raised when a invoked check fails.

    This inherits from :exc:`ApplicationCommandError`.
    """
    pass

class ApplicationCommandInvokeError(ApplicationCommandError):
    """Exception raised when the application command being invoked
    raised an exception.

    This inherits from :exc:`ApplicationCommandError`

    Attributes
    -----------
    original: :exc:`Exception`
        The original exception that was raised. You can also get this via
        the ``__cause__`` attribute.
    """
    def __init__(self, e: Exception) -> None:
        self.original: Exception = e
        super().__init__(f'Command raised an exception: {e.__class__.__name__}: {e}')


class ApplicationRegistrationError(ClientException):
    """An exception raised when the command can't be added
    because the name is already taken by a different command.

    This inherits from :exc:`discord.ClientException`

    Attributes
    ----------
    name: :class:`str`
        The command name that had the error.
    """
    def __init__(self, name: str) -> None:
        self.name: str = name
        super().__init__(f'The command \'{name}\' is already an existing command.')

class ApplicationRegistrationMaxDepthError(ClientException):
    """An exception raised when the command can't be added
    because the parent reach the maximum depth for more child.

    This inherits from :exc:`discord.ClientException`

    Attributes
    ----------
    name: :class:`str`
        The command name that had the error.
    parent_name: :class:`str`
        The parent command name.
    """
    def __init__(self, name: str, parent_name: str) -> None:
        self.name: str = name
        super().__init__(
            f'The command \'{name}\' cannot be registered to \'{parent_name}\' because '
            'it reach the maximum depth.'
        )

class ApplicationRegistrationExistingParentOptions(ClientException):
    """An exception raise when the command can't be added
    because the parent command contains and options that cannot be used
    if the child is a subcommand or group.

    This inherits from :exc:`discord.ClientException`

    Attributes
    -----------
    name: :class:`str`
        The command name that had the error.
    option: :class:`Option`
        The option that is not allowed.
    """
    def __init__(self, name: str, option: "Option") -> None:
        self.name: str = name
        self.option: str = option
        super().__init__(
            f'The command \'{name}\' cannot be registered since the parent command contains option \'{option.name}\''
            f' which is a type \'{option.input_type.name}\' (need to be subcommand or group)'
        )


class ApplicationUserInputError(ApplicationCommandError):
    """The base exception type for errors that involve errors
    regarding user input.

    This inherits from :exc:`ApplicationCommandError`.
    """
    pass

class ApplicationMissingRequiredArgument(ApplicationUserInputError):
    """Exception raised when parsing a command and a parameter
    that is required is not encountered.

    This inherits from :exc:`ApplicationUserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        The argument that is missing.
    """
    def __init__(self, command: str, param: Parameter) -> None:
        self.param: Parameter = param
        self.command: str = command
        super().__init__(f'Command {command} needs {param.name} which is a required argument that is missing.')

class ApplicationTooManyArguments(ApplicationUserInputError):
    """Exception raised when the command was passed too many arguments.

    This inherits from :exc:`ApplicationUserInputError`
    """
    pass

class ApplicationBadArgument(ApplicationUserInputError):
    """Exception raised when a parsing or conversion failure is encountered
    on an argument to pass into a command.

    This inherits from :exc:`ApplicationUserInputError`
    """
    pass

class ApplicationMemberNotFound(ApplicationBadArgument):
    """Exception raised when the member provided was not found in the bot's
    cache.

    This inherits from :exc:`ApplicationBadArgument`

    Attributes
    -----------
    argument: :class:`str`
        The member supplied by the caller that was not found
    """
    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'Member "{argument}" not found.')

class ApplicationMentionableNotFound(ApplicationBadArgument):
    """Exception raised when the mentionable provided was not found in the bot's
    cache.

    This inherits from :exc:`ApplicationBadArgument`

    Attributes
    -----------
    argument: :class:`str`
        The member supplied by the caller that was not found
    """
    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'Mentionable "{argument}" not found.')

class ApplicationUserNotFound(ApplicationBadArgument):
    """Exception raised when the user provided was not found in the bot's
    cache.

    This inherits from :exc:`ApplicationBadArgument`

    .. versionadded:: 1.5

    Attributes
    -----------
    argument: :class:`str`
        The user supplied by the caller that was not found
    """
    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'User "{argument}" not found.')

class ApplicationCommandOnCooldown(ApplicationCommandError):
    """Exception raised when the command being invoked is on cooldown.

    This inherits from :exc:`ApplicationCommandError`

    Attributes
    -----------
    cooldown: :class:`.ApplicationCooldown`
        A class with attributes ``rate`` and ``per`` similar to the
        :func:`.cooldown` decorator.
    type: :class:`BucketType`
        The type associated with the cooldown.
    retry_after: :class:`float`
        The amount of seconds to wait before you can retry again.
    """
    def __init__(self, cooldown: Cooldown, retry_after: float, type: BucketType) -> None:
        self.cooldown: Cooldown = cooldown
        self.retry_after: float = retry_after
        self.type: AppBucketType = type
        super().__init__(f'You are on cooldown. Try again in {retry_after:.2f}s')


# Check failure inherits

class ApplicationCheckAnyFailure(ApplicationCheckFailure):
    """Exception raised when all predicates in :func:`check_any` fail.

    This inherits from :exc:`ApplicationCheckFailure`.

    .. versionadded:: 1.3

    Attributes
    ------------
    errors: List[:class:`ApplicationCheckFailure`]
        A list of errors that were caught during execution.
    checks: List[Callable[[:class:`ApplicationContext`], :class:`bool`]]
        A list of check predicates that failed.
    """

    def __init__(
        self,
        checks: List[ApplicationCheckFailure],
        errors: List[Callable[["ApplicationContext"], bool]]
    ) -> None:
        self.checks: List[ApplicationCheckFailure] = checks
        self.errors: List[Callable[["ApplicationContext"], bool]] = errors
        super().__init__('You do not have permission to run this command.')

class ApplicationPrivateMessageOnly(ApplicationCheckFailure):
    """Exception raised when an operation does not work outside of private
    message contexts.

    This inherits from :exc:`ApplicationCheckFailure`
    """
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or 'This command can only be used in private messages.')

class ApplicationNoPrivateMessage(ApplicationCheckFailure):
    """Exception raised when an operation does not work in private message
    contexts.

    This inherits from :exc:`ApplicationCheckFailure`
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or 'This command cannot be used in private messages.')

class ApplicationMissingRole(ApplicationCheckFailure):
    """Exception raised when the command invoker lacks a role to run a command.

    This inherits from :exc:`ApplicationCheckFailure`

    Attributes
    -----------
    missing_role: Union[:class:`str`, :class:`int`]
        The required role that is missing.
        This is the parameter passed to :func:`~.app.has_role`.
    """
    def __init__(self, missing_role: "Snowflake") -> None:
        self.missing_role: "Snowflake" = missing_role
        message = f'Role {missing_role!r} is required to run this command.'
        super().__init__(message)

class ApplicationBotMissingRole(ApplicationCheckFailure):
    """Exception raised when the bot's member lacks a role to run a command.

    This inherits from :exc:`ApplicationCheckFailure`

    Attributes
    -----------
    missing_role: Union[:class:`str`, :class:`int`]
        The required role that is missing.
        This is the parameter passed to :func:`~.app.has_role`.
    """
    def __init__(self, missing_role: "Snowflake") -> None:
        self.missing_role: "Snowflake" = missing_role
        message = f'Bot requires the role {missing_role!r} to run this command'
        super().__init__(message)

class ApplicationMissingAnyRole(ApplicationCheckFailure):
    """Exception raised when the command invoker lacks any of
    the roles specified to run a command.

    This inherits from :exc:`ApplicationCheckFailure`

    .. versionadded:: 1.1

    Attributes
    -----------
    missing_roles: List[Union[:class:`str`, :class:`int`]]
        The roles that the invoker is missing.
        These are the parameters passed to :func:`~.app.has_any_role`.
    """
    def __init__(self, missing_roles: "SnowflakeList") -> None:
        self.missing_roles: "SnowflakeList" = missing_roles

        missing = [f"'{role}'" for role in missing_roles]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)

        message = f"You are missing at least one of the required roles: {fmt}"
        super().__init__(message)

class ApplicationBotMissingAnyRole(ApplicationCheckFailure):
    """Exception raised when the bot's member lacks any of
    the roles specified to run a command.

    This inherits from :exc:`ApplicationCheckFailure`

    .. versionadded:: 1.1

    Attributes
    -----------
    missing_roles: List[Union[:class:`str`, :class:`int`]]
        The roles that the bot's member is missing.
        These are the parameters passed to :func:`~.app.has_any_role`.

    """
    def __init__(self, missing_roles: "SnowflakeList") -> None:
        self.missing_roles: "SnowflakeList" = missing_roles

        missing = [f"'{role}'" for role in missing_roles]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)

        message = f"Bot is missing at least one of the required roles: {fmt}"
        super().__init__(message)

class ApplicationMissingPermissions(ApplicationCheckFailure):
    """Exception raised when the command invoker lacks permissions to run a
    command.

    This inherits from :exc:`ApplicationCheckFailure`

    Attributes
    -----------
    missing_permissions: List[:class:`str`]
        The required permissions that are missing.
    """
    def __init__(self, missing_permissions: List[str], *args: Any) -> None:
        self.missing_permissions: List[str] = missing_permissions

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_permissions]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'You are missing {fmt} permission(s) to run this command.'
        super().__init__(message, *args)

class ApplicationBotMissingPermissions(ApplicationCheckFailure):
    """Exception raised when the bot's member lacks permissions to run a
    command.

    This inherits from :exc:`ApplicationCheckFailure`

    Attributes
    -----------
    missing_permissions: List[:class:`str`]
        The required permissions that are missing.
    """
    def __init__(self, missing_permissions: List[str], *args: Any) -> None:
        self.missing_permissions: List[str] = missing_permissions

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_permissions]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'Bot requires {fmt} permission(s) to run this command.'
        super().__init__(message, *args)

class ApplicationNSFWChannelRequired(ApplicationCheckFailure):
    """Exception raised when a channel does not have the required NSFW setting.

    This inherits from :exc:`ApplicationCheckFailure`.

    .. versionadded:: 1.1

    Parameters
    -----------
    channel: Union[:class:`.abc.GuildChannel`, :class:`.Thread`]
        The channel that does not have NSFW enabled.
    """
    def __init__(self, channel: Union["GuildChannel", "Thread"]) -> None:
        self.channel: Union["GuildChannel", "Thread"] = channel
        super().__init__(f"Channel '{channel}' needs to be NSFW for this command to work.")

class ApplicationNotOwner(ApplicationCheckFailure):
    """Exception raised when the message author is not the owner of the bot.

    This inherits from :exc:`ApplicationCheckFailure`
    """
    pass
