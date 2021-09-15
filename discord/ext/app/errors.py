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

from discord.errors import ClientException, DiscordException

__all__ = (
    'ApplicationCommandError',
    'ApplicationCheckFailure',
    'ApplicationCommandInvokeError',
    'ApplicationRegistrationError',
)

class ApplicationCommandError(DiscordException):
    r"""The base exception type for all command related errors.

    This inherits from :exc:`discord.DiscordException`.

    This exception and exceptions inherited from it are handled
    in a special way as they are caught and passed into a special event
    from :class:`.Bot`\, :func:`.on_command_error`.
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
        super().__init__(f'The command {name} is already an existing command.')
