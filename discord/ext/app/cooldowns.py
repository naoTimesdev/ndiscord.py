"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz and naoTimesdev

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

# Adapted from ext.commands.Cooldown
# not much has changed except adapted for Interaction.

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, Deque, Dict, Optional, Type, TypeVar

from discord.enums import Enum

from .errors import ApplicationMaxConcurrencyReached

if TYPE_CHECKING:
    from ...interactions import Interaction

__all__ = (
    "ApplicationBucketType",
    "ApplicationCooldown",
    "ApplicationCooldownMapping",
    "ApplicationDynamicCooldownMapping",
    "ApplicationMaxConcurrency",
)

AC = TypeVar("AC", bound="ApplicationCooldownMapping")
AMC = TypeVar("AMC", bound="ApplicationMaxConcurrency")


class ApplicationBucketType(Enum):
    default = 0
    user = 1
    guild = 2
    channel = 3
    member = 4

    def get_key(self, inter: Interaction) -> Any:
        if self is ApplicationBucketType.user:
            return inter
        elif self is ApplicationBucketType.guild:
            return inter.guild.id
        elif self is ApplicationBucketType.channel:
            return inter.channel.id
        elif self is ApplicationBucketType.member:
            return ((inter.guild and inter.guild.id), inter.user.id)

    def __call__(self, msg: Interaction) -> Any:
        return self.get_key(msg)


class ApplicationCooldown:
    """Represents a cooldown for an application.

    Attributes
    -----------
    rate: :class:`int`
        The total number of tokens available per :attr:`per` seconds.
    per: :class:`float`
        The length of the cooldown period in seconds.
    """

    __slots__ = ("rate", "per", "_window", "_tokens", "_last")

    def __init__(self, rate: float, per: float) -> None:
        self.rate: int = int(rate)
        self.per: float = float(per)
        self._window: float = 0.0
        self._tokens: int = self.rate
        self._last: float = 0.0

    def get_tokens(self, current: Optional[float] = None) -> int:
        """Returns the number of available tokens before rate limiting is applied.

        Parameters
        ------------
        current: Optional[:class:`float`]
            The time in seconds since Unix epoch to calculate tokens at.
            If not supplied then :func:`time.time()` is used.

        Returns
        --------
        :class:`int`
            The number of tokens available before the cooldown is to be applied.
        """
        if not current:
            current = time.time()

        tokens = self._tokens

        if current > self._window + self.per:
            tokens = self.rate
        return tokens

    def get_retry_after(self, current: Optional[float] = None) -> float:
        """Returns the time in seconds until the cooldown will be reset.

        Parameters
        -------------
        current: Optional[:class:`float`]
            The current time in seconds since Unix epoch.
            If not supplied, then :func:`time.time()` is used.

        Returns
        -------
        :class:`float`
            The number of seconds to wait before this cooldown will be reset.
        """
        current = current or time.time()
        tokens = self.get_tokens(current)

        if tokens == 0:
            return self.per - (current - self._window)

        return 0.0

    def update_rate_limit(self, current: Optional[float] = None) -> Optional[float]:
        """Updates the cooldown rate limit.

        Parameters
        -------------
        current: Optional[:class:`float`]
            The time in seconds since Unix epoch to update the rate limit at.
            If not supplied, then :func:`time.time()` is used.

        Returns
        -------
        Optional[:class:`float`]
            The retry-after time in seconds if rate limited.
        """
        current = current or time.time()
        self._last = current

        self._tokens = self.get_tokens(current)

        # first token used means that we start a new rate limit window
        if self._tokens == self.rate:
            self._window = current

        # check if we are rate limited
        if self._tokens == 0:
            return self.per - (current - self._window)

        # we're not so decrement our tokens
        self._tokens -= 1

    def reset(self) -> None:
        """Reset the cooldown to its initial state."""
        self._tokens = self.rate
        self._last = 0.0

    def copy(self) -> ApplicationCooldown:
        """Creates a copy of this cooldown.

        Returns
        --------
        :class:`ApplicationCooldown`
            A new instance of this cooldown.
        """
        return ApplicationCooldown(self.rate, self.per)

    def __repr__(self) -> str:
        return f"<ApplicationCooldown rate: {self.rate} per: {self.per} window: {self._window} tokens: {self._tokens}>"


class ApplicationCooldownMapping:
    def __init__(
        self,
        original: Optional[ApplicationCooldown],
        type: Callable[[Interaction], Any],
    ) -> None:
        if not callable(type):
            raise TypeError("Cooldown type must be a ApplicationBucketType or callable")

        self._cache: Dict[Any, ApplicationBucketType] = {}
        self._cooldown: Optional[ApplicationCooldown] = original
        self._type: Callable[[Interaction], Any] = type

    def copy(self) -> ApplicationCooldownMapping:
        ret = ApplicationCooldownMapping(self._cooldown, self._type)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self) -> bool:
        return self._cooldown is not None

    @property
    def type(self) -> Callable[[Interaction], Any]:
        return self._type

    @classmethod
    def from_cooldown(cls: Type[AC], rate, per, type) -> AC:
        return cls(ApplicationCooldown(rate, per), type)

    def _bucket_key(self, msg: Interaction) -> Any:
        return self._type(msg)

    def _verify_cache_integrity(self, current: Optional[float] = None) -> None:
        # we want to delete all cache objects that haven't been used
        # in a cooldown window. e.g. if we have a  command that has a
        # cooldown of 60s and it has not been used in 60s then that key should be deleted
        current = current or time.time()
        dead_keys = [k for k, v in self._cache.items() if current > v._last + v.per]
        for k in dead_keys:
            del self._cache[k]

    def create_bucket(self, interaction: Interaction) -> ApplicationCooldown:
        return self._cooldown.copy()  # type: ignore

    def get_bucket(self, interaction: Interaction, current: Optional[float] = None) -> ApplicationCooldown:
        if self._type is ApplicationBucketType.default:
            return self._cooldown  # type: ignore

        self._verify_cache_integrity(current)
        key = self._bucket_key(interaction)
        if key not in self._cache:
            bucket = self.create_bucket(interaction)
            if bucket is not None:
                self._cache[key] = bucket
        else:
            bucket = self._cache[key]

        return bucket

    def update_rate_limit(self, interaction: Interaction, current: Optional[float] = None) -> Optional[float]:
        bucket = self.get_bucket(interaction, current)
        return bucket.update_rate_limit(current)


class ApplicationDynamicCooldownMapping(ApplicationCooldownMapping):
    def __init__(
        self,
        factory: Callable[[Interaction], ApplicationCooldown],
        type: Callable[[Interaction], Any],
    ) -> None:
        super().__init__(None, type)
        self._factory = factory

    def copy(self) -> ApplicationDynamicCooldownMapping:
        ret = ApplicationDynamicCooldownMapping(self._factory, self._type)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self) -> bool:
        return True

    def create_bucket(self, interaction: Interaction) -> ApplicationCooldown:
        return self._factory(interaction)


class _Semaphore:
    """This class is a version of a semaphore.

    If you're wondering why asyncio.Semaphore isn't being used,
    it's because it doesn't expose the internal value. This internal
    value is necessary because I need to support both `wait=True` and
    `wait=False`.

    An asyncio.Queue could have been used to do this as well -- but it is
    not as inefficient since internally that uses two queues and is a bit
    overkill for what is basically a counter.
    """

    __slots__ = ("value", "loop", "_waiters")

    def __init__(self, number: int) -> None:
        self.value: int = number
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._waiters: Deque[asyncio.Future] = deque()

    def __repr__(self) -> str:
        return f"<_Semaphore value={self.value} waiters={len(self._waiters)}>"

    def locked(self) -> bool:
        return self.value == 0

    def is_active(self) -> bool:
        return len(self._waiters) > 0

    def wake_up(self) -> None:
        while self._waiters:
            future = self._waiters.popleft()
            if not future.done():
                future.set_result(None)
                return

    async def acquire(self, *, wait: bool = False) -> bool:
        if not wait and self.value <= 0:
            # signal that we're not acquiring
            return False

        while self.value <= 0:
            future = self.loop.create_future()
            self._waiters.append(future)
            try:
                await future
            except:  # noqa
                future.cancel()
                if self.value > 0 and not future.cancelled():
                    self.wake_up()
                raise

        self.value -= 1
        return True

    def release(self) -> None:
        self.value += 1
        self.wake_up()


class ApplicationMaxConcurrency:
    __slots__ = ("number", "per", "wait", "_mapping")

    def __init__(
        self,
        number: int,
        *,
        per: ApplicationBucketType,
        wait: bool,
    ) -> None:
        self._mapping: Dict[Any, _Semaphore] = {}
        self.per: ApplicationBucketType = per
        self.number: int = number
        self.wait: bool = wait

        if number <= 0:
            raise ValueError("max_concurrency 'number' cannot be less than 1")

        if not isinstance(per, ApplicationBucketType):
            raise TypeError(f"max_concurrency 'per' must be of type ApplicationBucketType not {type(per)!r}")

    def copy(self: AMC) -> AMC:
        return self.__class__(self.number, per=self.per, wait=self.wait)

    def __repr__(self) -> str:
        return f"<ApplicationMaxConcurrency per={self.per!r} number={self.number} wait={self.wait}>"

    def get_key(self, interaction: Interaction) -> Any:
        return self.per.get_key(interaction)

    async def acquire(self, interaction: Interaction) -> None:
        key = self.get_key(interaction)

        try:
            sem = self._mapping[key]
        except KeyError:
            self._mapping[key] = sem = _Semaphore(self.number)

        acquired = await sem.acquire(wait=self.wait)
        if not acquired:
            raise ApplicationMaxConcurrencyReached(self.number, self.per)

    async def release(self, interaction: Interaction) -> None:
        # Technically there's no reason for this function to be async
        # But it might be more useful in the future
        key = self.get_key(interaction)

        try:
            sem = self._mapping[key]
        except KeyError:
            # ...? peculiar
            return
        else:
            sem.release()

        if sem.value >= self.number and not sem.is_active():
            del self._mapping[key]
