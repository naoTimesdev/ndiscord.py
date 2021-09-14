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
from typing import Any, Callable, Coroutine, TYPE_CHECKING, List, Protocol, TypeVar, Union

if TYPE_CHECKING:
    from .context import ApplicationContext
    from .errors import ApplicationCommandError
    from discord.ext.commands import Cog

T = TypeVar('T')

Coro = Coroutine[Any, Any, T]
MaybeCoro = Union[T, Coro[T]]
CoroFunc = Callable[..., Coro[Any]]
CogT = TypeVar('CogT', bound='Cog')

Check = Union[Callable[["Cog", "ApplicationContext"], MaybeCoro[bool]], Callable[["ApplicationContext"], MaybeCoro[bool]]]
Hook = Union[Callable[["Cog", "ApplicationContext"], Coro[Any]], Callable[["ApplicationContext"], Coro[Any]]]
Error = Union[Callable[["Cog", "ApplicationContext", "ApplicationCommandError"], Coro[Any]], Callable[["ApplicationContext", "ApplicationCommandError"], Coro[Any]]]

class ApplicationCallback(Protocol):
    """A callback that can be used by an :class:`ApplicationCommand`."""

    __commands_checks__: List[Check]
    __before_invoke__: Hook
    __after_invoke__: Hook

    def __call__(self, ctx: ApplicationContext, *args: Any, **kwargs: Any) -> Any:
        ...

# Same thing as what ext.commands._types do
class _BaseApplication:
    __slots__ = ()
