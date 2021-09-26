"""
The MIT License (MIT)

Copyright (c) 2021-present naoTimesdev and Imayhaveborkedit

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

import bisect
import logging
import threading
import time
import traceback
from typing import Any, Callable, Generator, List, Optional, Tuple

from discord import utils
from discord.opus import Decoder

from .rtp import *

log = logging.getLogger(__name__)

SinkCallable = Callable[[bytes, bytes, Any], None]

__all__ = (
    "BufferedDecoder",
    "BufferedPacketDecoder",
)


class BufferedDecoder(threading.Thread):
    DELAY = Decoder.FRAME_LENGTH / 1000.0

    def __init__(self, ssrc: int, sink: SinkCallable, *, buffer: int = 200):
        super().__init__(daemon=True, name=f"ssrc-{ssrc}")

        if buffer < 40:  # technically 20 works but then FEC is useless
            raise ValueError(f"buffer size of {buffer} is invalid; cannot be lower than 40")

        self.ssrc: int = ssrc
        self.sink: SinkCallable = sink

        self._decoder = Decoder()
        self._buffer: List[RTPPacket] = []
        self._last_seq = 0
        self._last_ts = 0
        self._loops = 0

        # Optional diagnostic state stuff
        self._overflow_mult = self._overflow_base = 2.0
        self._overflow_incr: float = 0.5

        # minimum (lower bound) size of the jitter buffer (n * 20ms per packet)
        self.buffer_size: int = buffer // self._decoder.FRAME_LENGTH

        self._finalizing: bool = False
        self._end_thread = threading.Event()
        self._end_main_loop = threading.Event()
        self._primed = threading.Event()
        self._lock = threading.RLock()

        # TODO: Add RTCP queue
        self._rtcp_buffer = {}

    def feed_rtp(self, packet: RTPPacket):
        if self._last_ts < packet.timestamp:
            self._push(packet)
        elif self._end_thread.is_set():
            return

    def feed_rtcp(self, packet: RTCPPacket):
        with self._lock:
            if not self._buffer:
                return
            self._rtcp_buffer[self._buffer[-1]] = packet

    def truncate(self, *, size: int = None):
        """Discards old data to shrink buffer back down to ``size`` or the buffer size.

        Parameters
        -----------
        size: Optional[:class:`int`]
            The size to truncate the buffer to. If not provided, will use the buffer size
        """

        size = self.buffer_size if size is None else size
        with self._lock:
            self._buffer = self._buffer[-size:]

    def stop(self, *, drain: bool = True, flush: bool = False):
        """Stop the thread and decoder from running.

        Parameters
        -----------
        drain: :class:`bool`
            If ``True``, will wait for the buffer to write out the remainder of the buffer
            at a standard rate.
        flush: :class:`bool`
            If ``True``, will flush the remainder of the buffer with no delay.
        """

        with self._lock:
            self._end_thread.set()
            self._end_main_loop.set()

            if any(isinstance(p, RTPPacket) for p in self._buffer) or True:
                if flush:
                    self._finalizing = True
                    self.DELAY = 0
                elif not drain:
                    with self._lock:
                        self._finalizing = True
                        self._buffer.clear()

    def reset(self):
        """Reset the decoder and clear the buffer."""
        with self._lock:
            self._decoder = Decoder()  # TODO: Add a reset function to Decoder itself
            self._last_seq = self._last_ts = 0
            self._buffer.clear()
            self._rtcp_buffer.clear()
            self._primed.clear()
            self._end_main_loop.set()  # XXX: racy with _push?
            self.DELAY = self.__class__.DELAY

    def _push(self, item: RTPPacket):
        if not isinstance(item, (RTPPacket, SilencePacket)):
            raise TypeError(f"item should be an RTPPacket, not {item.__class__.__name__}")

        # XXX: racy with reset?
        if self._end_main_loop.is_set() and not self._end_thread.is_set():
            self._end_main_loop.clear()

        if not self._primed.is_set():
            self._primed.set()

        # Fake packet loss
        # import random
        # if random.randint(1, 100) <= 10 and isinstance(item, RTPPacket):
        #     return

        with self._lock:
            existing_packet = utils.get(self._buffer, timestamp=item.timestamp)
            if isinstance(existing_packet, SilencePacket):
                # Replace silence packets with rtp packets
                self._buffer[self._buffer.index(existing_packet)] = item
                return
            elif isinstance(existing_packet, RTPPacket):
                return  # duplicate packet

            bisect.insort(self._buffer, item)

            # Optional diagnostics, will probably remove later
            bufsize = len(self._buffer)  # indent intentional
        if bufsize >= self.buffer_size * self._overflow_mult:
            print(f"[router:push] Warning: rtp heap size has grown to {bufsize}")
            self._overflow_mult += self._overflow_incr

        elif (
            bufsize <= self.buffer_size * (self._overflow_mult - self._overflow_incr)
            and self._overflow_mult > self._overflow_base
        ):

            print(f"[router:push] Info: rtp heap size has shrunk to {bufsize}")
            self._overflow_mult = max(self._overflow_base, self._overflow_mult - self._overflow_incr)

    def _pop(self) -> Tuple[RTPPacket, RTPPacket]:
        packet = nextpacket = None
        with self._lock:
            try:
                if not self._finalizing:
                    self._buffer.append(
                        SilencePacket(self.ssrc, self._buffer[-1].timestamp + Decoder.SAMPLES_PER_FRAME)
                    )
                packet = self._buffer.pop(0)
                nextpacket = self._buffer[0]
            except IndexError:
                pass  # empty buffer

        return packet, nextpacket

    def _initial_fill(self):
        """Artisanal hand-crafted function for buffering packets and clearing discord's stupid fucking rtp buffer."""

        if self._end_main_loop.is_set():
            return

        # Very small sleep to check if there's buffered packets
        time.sleep(0.001)
        if len(self._buffer) > 3:
            # looks like there's some old packets in the buffer
            # we need to figure out where the old packets stop and where the fresh ones begin
            # for that we need to see when we return to the normal packet accumulation rate

            last_size = len(self._buffer)

            # wait until we have the correct rate of packet ingress
            while len(self._buffer) - last_size > 1:
                last_size = len(self._buffer)
                time.sleep(0.001)

            # collect some fresh packets
            time.sleep(0.06)

            # generate list of differences between packet sequences
            with self._lock:
                diffs = [self._buffer[i + 1].sequence - self._buffer[i].sequence for i in range(len(self._buffer) - 1)]
            sdiffs = sorted(diffs, reverse=True)

            # decide if there's a jump
            jump1, jump2 = sdiffs[:2]
            if jump1 > jump2 * 3:
                # remove the stale packets and keep the fresh ones
                self.truncate(size=len(self._buffer[diffs.index(jump1) + 1 :]))
            else:
                # otherwise they're all stale, dump 'em (does this ever happen?)
                with self._lock:
                    self._buffer.clear()

        # fill buffer to at least half full
        while len(self._buffer) < self.buffer_size // 2:
            time.sleep(0.001)

        # fill the buffer with silence aligned with the first packet
        # if an rtp packet already exists for the given silence packet ts, the silence packet is ignored
        with self._lock:
            start_ts = self._buffer[0].timestamp
            for x in range(1, 1 + self.buffer_size - len(self._buffer)):
                self._push(SilencePacket(self.ssrc, start_ts + x * Decoder.SAMPLES_PER_FRAME))

        # now fill the rest
        while len(self._buffer) < self.buffer_size:
            time.sleep(0.001)
            # TODO: Maybe only wait at most for about as long we we're supposed to?
            #       0.02 * (buffersize - len(buffer))

    def _packet_gen(self) -> Generator[Tuple[RTPPacket, bytes], None, None]:
        while True:
            packet, nextpacket = self._pop()
            self._last_ts = getattr(packet, "timestamp", self._last_ts + Decoder.SAMPLES_PER_FRAME)
            self._last_seq += 1  # self._last_seq = packet.sequence?

            if isinstance(packet, RTPPacket):
                pcm = self._decoder.decode(packet.decrypted_data)

            elif isinstance(nextpacket, RTPPacket):
                pcm = self._decoder.decode(packet.decrypted_data, fec=True)
                fec_packet = FECPacket(
                    self.ssrc, nextpacket.sequence - 1, nextpacket.timestamp - Decoder.SAMPLES_PER_FRAME
                )
                yield fec_packet, pcm

                packet, _ = self._pop()
                self._last_ts += Decoder.SAMPLES_PER_FRAME
                self._last_seq += 1

                pcm = self._decoder.decode(packet.decrypted_data)

            elif packet is None:
                self._finalizing = False
                break
            else:
                pcm = self._decoder.decode(None)

            yield packet, pcm

    def _do_run(self):
        self._primed.wait()
        self._initial_fill()

        self._loops = 0
        packet_gen = self._packet_gen()
        start_time = time.perf_counter()
        try:
            while not self._end_main_loop.is_set() or self._finalizing:
                packet, pcm = next(packet_gen)
                try:
                    self.sink(pcm, packet.decrypted_data, packet)
                except Exception:
                    log.exception("Sink raised exception")
                    traceback.print_exc()

                next_time = start_time + self.DELAY * self._loops
                self._loops += 1

                time.sleep(max(0, self.DELAY + (next_time - time.perf_counter())))
        except StopIteration:
            time.sleep(0.001)  # just in case, so we don't slam the cpu
        finally:
            packet_gen.close()

    def run(self):
        try:
            while not self._end_thread.is_set():
                self._do_run()
        except Exception:
            log.exception("Error in decoder %s", self.name)
            traceback.print_exc()


class BasePacketDecoder:
    DELAY = Decoder.FRAME_LENGTH / 1000.0

    def feed_rtp(self, packet: RTCPPacket):
        raise NotImplementedError

    def feed_rtcp(self, packet: RTCPPacket):
        raise NotImplementedError

    def truncate(self, *, size: Optional[int] = None):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


class BufferedPacketDecoder(BasePacketDecoder):
    """Buffers and decodes packets from a single ssrc"""
