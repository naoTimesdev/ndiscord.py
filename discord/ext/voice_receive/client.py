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
import logging
import socket
import struct
import threading
from typing import TYPE_CHECKING, Any, List, Optional

from discord import opus, utils
from discord.backoff import ExponentialBackoff
from discord.errors import ClientException, ConnectionClosed
from discord.gateway import DiscordVoiceWebSocket
from discord.voice_client import VoiceProtocol

from .bidict import Bidict
from .reader import AudioReader, AudioSink

if TYPE_CHECKING:
    from discord import abc
    from discord.client import Client
    from discord.guild import Guild
    from discord.state import ConnectionState
    from discord.types.voice import GuildVoiceState as GuildVoiceStatePayload
    from discord.types.voice import VoiceServerUpdate as VoiceServerUpdatePayload
    from discord.user import ClientUser


has_nacl: bool
try:
    import nacl.secret  # noqa

    has_nacl = True
except ImportError:
    has_nacl = False


MISSING: Any = utils.MISSING

_log = logging.getLogger(__name__)


class VoiceClientReceiver(VoiceProtocol):
    """Represents a Discord voice connection.

    This implementation is mostly the same as :class:`VoiceClient`
    with the difference that this is for receiving audio.

    You do not create these, you typically get them from
    e.g. :meth:`VoiceChannel.connect`.

    Warning
    --------
    In order to use PCM based AudioSources, you must have the opus library
    installed on your system and loaded through :func:`opus.load_opus`.
    Otherwise, your AudioSources must be opus encoded (e.g. using :class:`FFmpegOpusAudio`)
    or the library will not be able to transmit audio.

    Examples
    ----------

    Getting the VoiceClientReceiver class ::

        async def listen(self, ctx):
            vc: VoiceClientReceiver = ctx.author.voice.channel.connect(cls=VoiceClientReceiver)

    Attributes
    -----------
    session_id: :class:`str`
        The voice connection session ID.
    token: :class:`str`
        The voice connection token.
    endpoint: :class:`str`
        The endpoint we are connecting to.
    channel: :class:`abc.Connectable`
        The voice channel connected to.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop that the voice client is running on.
    """

    endpoint_ip: str
    voice_port: int
    secret_key: List[int]
    ssrc: int
    ip: str
    port: int

    # Some dirty hack for checking
    _client_type = "receive"

    def __init__(self, client: Client, channel: abc.Connectable):
        if not has_nacl:
            raise RuntimeError("PyNaCl library needed in order to use voice")

        super().__init__(client, channel)
        state = client._connection
        self.token: str = MISSING
        self.socket = MISSING
        self.loop: asyncio.AbstractEventLoop = state.loop
        self._state: ConnectionState = state
        # this will be used in the AudioPlayer thread
        self._connected: threading.Event = threading.Event()
        # this will be used in the AudioReader thread
        self._connecting = threading.Condition()

        self._handshaking: bool = False
        self._potentially_reconnecting: bool = False
        self._voice_state_complete: asyncio.Event = asyncio.Event()
        self._voice_server_complete: asyncio.Event = asyncio.Event()

        self._mode: str = MISSING
        self._connections: int = 0
        self.sequence: int = 0
        self.timestamp: int = 0
        self.timeout: float = 0
        self.encoder: opus.Encoder = MISSING
        self._runner: asyncio.Task = MISSING
        self._reader = None
        self.ws: DiscordVoiceWebSocket = MISSING
        self._ssrcs = Bidict()

    warn_nacl = not has_nacl
    supported_modes = (
        "xsalsa20_poly1305_lite",
        "xsalsa20_poly1305_suffix",
        "xsalsa20_poly1305",
    )

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`Guild`]: The guild we're connected to, if applicable."""
        return getattr(self.channel, "guild", None)

    @property
    def user(self) -> ClientUser:
        """:class:`ClientUser`: The user connected to voice (i.e. ourselves)."""
        return self._state.user

    def checked_add(self, attr, value, limit):
        val = getattr(self, attr)
        if val + value > limit:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, val + value)

    # connection related

    async def on_voice_state_update(self, data: GuildVoiceStatePayload) -> None:
        self.session_id = data["session_id"]
        channel_id = data["channel_id"]

        if not self._handshaking or self._potentially_reconnecting:
            # If we're done handshaking then we just need to update ourselves
            # If we're potentially reconnecting due to a 4014, then we need to differentiate
            # a channel move and an actual force disconnect
            if channel_id is None:
                # We're being disconnected so cleanup
                await self.disconnect()
            else:
                guild = self.guild
                self.channel = channel_id and guild and guild.get_channel(int(channel_id))  # type: ignore
        else:
            self._voice_state_complete.set()

    async def on_voice_server_update(self, data: VoiceServerUpdatePayload) -> None:
        if self._voice_server_complete.is_set():
            _log.info("Ignoring extraneous voice server update.")
            return

        self.token = data.get("token")
        self.server_id = int(data["guild_id"])
        endpoint = data.get("endpoint")

        if endpoint is None or self.token is None:
            _log.warning(
                "Awaiting endpoint... This requires waiting. "
                "If timeout occurred considering raising the timeout and reconnecting."
            )
            return

        self.endpoint, _, _ = endpoint.rpartition(":")
        if self.endpoint.startswith("wss://"):
            # Just in case, strip it off since we're going to add it later
            self.endpoint = self.endpoint[6:]

        # This gets set later
        self.endpoint_ip = MISSING

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)

        if not self._handshaking:
            # If we're not handshaking then we need to terminate our previous connection in the websocket
            await self.ws.close(4000)
            return

        self._voice_server_complete.set()

    async def voice_connect(self) -> None:
        await self.channel.guild.change_voice_state(channel=self.channel)

    async def voice_disconnect(self) -> None:
        _log.info(
            "The voice handshake is being terminated for Channel ID %s (Guild ID %s)", self.channel.id, self.guild.id
        )
        await self.channel.guild.change_voice_state(channel=None)

    def prepare_handshake(self) -> None:
        self._voice_state_complete.clear()
        self._voice_server_complete.clear()
        self._handshaking = True
        _log.info("Starting voice handshake... (connection attempt %d)", self._connections + 1)
        self._connections += 1

    def finish_handshake(self) -> None:
        _log.info("Voice handshake complete. Endpoint found %s", self.endpoint)
        self._handshaking = False
        self._voice_server_complete.clear()
        self._voice_state_complete.clear()

    async def connect_websocket(self) -> DiscordVoiceWebSocket:
        ws = await DiscordVoiceWebSocket.from_client(self)
        self._connected.clear()
        while ws.secret_key is None:
            await ws.poll_event()
        self._connected.set()
        return ws

    async def connect(self, *, reconnect: bool, timeout: float) -> None:
        _log.info("Connecting to voice...")
        self.timeout = timeout

        for i in range(5):
            self.prepare_handshake()

            # This has to be created before we start the flow.
            futures = [
                self._voice_state_complete.wait(),
                self._voice_server_complete.wait(),
            ]

            # Start the connection flow
            await self.voice_connect()

            try:
                await utils.sane_wait_for(futures, timeout=timeout)
            except asyncio.TimeoutError:
                await self.disconnect(force=True)
                raise

            self.finish_handshake()

            try:
                self.ws = await self.connect_websocket()
                break
            except (ConnectionClosed, asyncio.TimeoutError):
                if reconnect:
                    _log.exception("Failed to connect to voice... Retrying...")
                    await asyncio.sleep(1 + i * 2.0)
                    await self.voice_disconnect()
                    continue
                else:
                    raise

        if self._runner is MISSING:
            self._runner = self.loop.create_task(self.poll_voice_ws(reconnect))

    async def potential_reconnect(self) -> bool:
        # Attempt to stop the player thread from playing early
        self._connected.clear()
        self.prepare_handshake()
        self._potentially_reconnecting = True
        try:
            # We only care about VOICE_SERVER_UPDATE since VOICE_STATE_UPDATE can come before we get disconnected
            await asyncio.wait_for(self._voice_server_complete.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            self._potentially_reconnecting = False
            await self.disconnect(force=True)
            return False

        self.finish_handshake()
        self._potentially_reconnecting = False
        try:
            self.ws = await self.connect_websocket()
        except (ConnectionClosed, asyncio.TimeoutError):
            return False
        else:
            return True

    @property
    def latency(self) -> float:
        """:class:`float`: Latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds.

        This could be referred to as the Discord Voice WebSocket latency and is
        an analogue of user's voice latencies as seen in the Discord client.

        .. versionadded:: 1.4
        """
        ws = self.ws
        return float("inf") if not ws else ws.latency

    @property
    def average_latency(self) -> float:
        """:class:`float`: Average of most recent 20 HEARTBEAT latencies in seconds.

        .. versionadded:: 1.4
        """
        ws = self.ws
        return float("inf") if not ws else ws.average_latency

    async def poll_voice_ws(self, reconnect: bool) -> None:
        backoff = ExponentialBackoff()
        while True:
            try:
                await self.ws.poll_event()
            except (ConnectionClosed, asyncio.TimeoutError) as exc:
                if isinstance(exc, ConnectionClosed):
                    # The following close codes are undocumented so I will document them here.
                    # 1000 - normal closure (obviously)
                    # 4014 - voice channel has been deleted.
                    # 4015 - voice server has crashed
                    if exc.code in (1000, 4015):
                        _log.info("Disconnecting from voice normally, close code %d.", exc.code)
                        await self.disconnect()
                        break
                    if exc.code == 4014:
                        _log.info("Disconnected from voice by force... potentially reconnecting.")
                        successful = await self.potential_reconnect()
                        if not successful:
                            _log.info("Reconnect was unsuccessful, disconnecting from voice normally...")
                            await self.disconnect()
                            break
                        else:
                            continue

                if not reconnect:
                    await self.disconnect()
                    raise

                retry = backoff.delay()
                _log.exception("Disconnected from voice... Reconnecting in %.2fs.", retry)
                self._connected.clear()
                await asyncio.sleep(retry)
                await self.voice_disconnect()
                try:
                    await self.connect(reconnect=True, timeout=self.timeout)
                except asyncio.TimeoutError:
                    # at this point we've retried 5 times... let's continue the loop.
                    _log.warning("Could not connect to voice... Retrying...")
                    continue

    async def disconnect(self, *, force: bool = False) -> None:
        """|coro|

        Disconnects this voice client from voice.
        """
        if not force and not self.is_connected():
            return

        self.stop()
        self._connected.clear()

        try:
            if self.ws:
                await self.ws.close()

            await self.voice_disconnect()
        finally:
            self.cleanup()
            if self.socket:
                self.socket.close()

    async def move_to(self, channel: abc.Snowflake) -> None:
        """|coro|

        Moves you to a different voice channel.

        Parameters
        -----------
        channel: :class:`abc.Snowflake`
            The channel to move to. Must be a voice channel.
        """
        await self.channel.guild.change_voice_state(channel=channel)

    def is_connected(self) -> bool:
        """Indicates if the voice client is connected to voice."""
        return self._connected.is_set()

    # audio related

    def _add_ssrc(self, user_id, ssrc):
        """Adds a user_id<->ssrc mapping.
        Technically these can be added in either order, but using user_id as the key
        is preferable since, should we be updating a mapping instead of adding one, we
        want to update the ssrc for the user_id, not the other way around.
        I think?  Did I write it to work like that?
        """
        self._ssrcs[user_id] = ssrc

    def _remove_ssrc(self, *, ssrc=None, user_id=None):
        """Removes a user_id<->ssrc mapping.  Either one can be used as the key."""

        thing = ssrc or user_id
        if not thing:
            raise TypeError("must provide at least one argument")

        other_thing = self._ssrcs.pop(thing, None)
        if self._reader:
            self._reader._ssrc_removed(ssrc or other_thing)

    def _get_ssrc_mapping(self, *, ssrc=None, user_id=None):
        """Returns a (ssrc, user_id) tuple from the given input.  At least one argument is required."""

        thing = ssrc or user_id
        if not thing:
            raise TypeError("must provide at least one argument")

        other_thing = self._ssrcs.get(thing)
        return ssrc or other_thing, user_id or other_thing

    def _encrypt_voice_packet(self, data):
        header = bytearray(12)

        # Formulate rtp header
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into(">H", header, 2, self.sequence)
        struct.pack_into(">I", header, 4, self.timestamp)
        struct.pack_into(">I", header, 8, self.ssrc)

        encrypt_packet = getattr(self, "_encrypt_" + self._mode)
        return encrypt_packet(header, data)

    def send_audio_packet(self, data: bytes, *, encode: bool = True) -> None:
        """Sends an audio packet composed of the data.

        You must be connected to play audio.

        Parameters
        ----------
        data: :class:`bytes`
            The :term:`py:bytes-like object` denoting PCM or Opus voice data.
        encode: :class:`bool`
            Indicates if ``data`` should be encoded into Opus.

        Raises
        -------
        ClientException
            You are not connected.
        opus.OpusError
            Encoding the data failed.
        """

        self.checked_add('sequence', 1, 65535)
        if encode:
            if self.encoder is MISSING:
                self.encoder = opus.Encoder()

            encoded_data = self.encoder.encode(data, opus.Encoder.SAMPLES_PER_FRAME)
        else:
            encoded_data = data

        packet = self._encrypt_voice_packet(encoded_data)

        try:
            self.socket.sendto(packet, (self.endpoint_ip, self.voice_port))
        except BlockingIOError:
            _log.warning('A packet has been dropped (seq: %s, timestamp: %s)', self.sequence, self.timestamp)

        self.checked_add('timestamp', opus.Encoder.SAMPLES_PER_FRAME, 4294967295)

    # receive api related

    def listen(self, sink: AudioSink):
        """Receives audio into a :class:`AudioSink`. TODO: wording
        TODO: the rest of it
        """

        if not self.is_connected():
            raise ClientException("Not connected to voice.")

        if not isinstance(sink, AudioSink):
            raise TypeError("sink must be an AudioSink not {0.__class__.__name__}".format(sink))

        if self.is_listening():
            raise ClientException("Already receiving audio.")

        self._reader = AudioReader(sink, self)
        self._reader.start()

    def is_listening(self):
        """Indicates if we're currently receiving audio."""
        return self._reader is not None and self._reader.is_listening()

    def stop(self):
        """Stops receiving audio."""
        if self._reader:
            self._reader.stop()
            self._reader = None

    @property
    def sink(self):
        return self._reader.sink if self._reader else None

    @sink.setter
    def sink(self, value):
        if not isinstance(value, AudioSink):
            raise TypeError("expected AudioSink not {0.__class__.__name__}.".format(value))

        if self._reader is None:
            raise ValueError("Not receiving anything.")

        self._reader._set_sink(value)
