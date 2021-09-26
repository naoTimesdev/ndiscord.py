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

import struct
import logging

from math import ceil
from enums import Enum

from typing import Any, Dict, List, NamedTuple, Optional, Sequence

log = logging.getLogger(__name__)

__all__ = ("RTPPacket", "RTCPPacket", "SilencePacket", "ExtensionID", "FECPacket")


class ExtensionID(Enum):
    audio_power = 1
    speaking_state = 9


class Extension(NamedTuple):
    profile: bytes
    length: int
    values: bytes


class RRSenderInfo(NamedTuple):
    ntp_rs: Any
    rtp_ts: Any
    packet_count: int
    octet_count: int


class RReport(NamedTuple):
    ssrc: int
    perc_loss: float
    total_lost: float
    last_seq: int
    jitter: int
    lsr: Any
    dlsr: Any


class SDESItem(NamedTuple):
    type: int
    size: int
    length: int
    text: Optional[Any]


class SDESChunk(NamedTuple):
    ssrc: int
    items: List[SDESItem]


def decode(data: bytes):
    """Create a :class:`RTPPacket` or a :class:`RTCPPacket`.

    Parameters
    -----------
    data: :class:`bytes`
        The packet data.
    """

    # While technically unreliable, discord RTP packets (should)
    # always be distinguishable from RTCP packets.  RTCP packets
    # should always have 200-204 as their second byte, while RTP
    # packet are (probably) always 73 (or at least not 200-204).

    assert data[0] >> 6 == 2  # check version bits
    return _rtcp_map.get(data[1], RTPPacket)(data)


def is_rtcp(data: bytes) -> bool:
    return 200 <= data[1] <= 204


def _parse_low(x: int):
    return x / 2.0 ** x.bit_length()


class _PacketCmpMixin:
    __slots__ = ()
    ssrc: int
    timestamp: int

    def __lt__(self, other):
        if self.ssrc != other.ssrc:
            raise TypeError("packet ssrc mismatch (%s, %s)" % (self.ssrc, other.ssrc))
        return self.timestamp < other.timestamp

    def __gt__(self, other):
        if self.ssrc != other.ssrc:
            raise TypeError("packet ssrc mismatch (%s, %s)" % (self.ssrc, other.ssrc))
        return self.timestamp > other.timestamp

    def __eq__(self, other):
        if self.ssrc != other.ssrc:
            raise TypeError("packet ssrc mismatch (%s, %s)" % (self.ssrc, other.ssrc))
        return self.timestamp == other.timestamp


class SilencePacket(_PacketCmpMixin):
    __slots__ = ("ssrc", "timestamp")
    decrypted_data = b"\xF8\xFF\xFE"

    def __init__(self, ssrc: int, timestamp: int):
        self.srrc: int = ssrc
        self.timestamp: int = timestamp

    def __repr__(self) -> str:
        return f"<SilencePacket timestamp={self.timestamp} ssrc={self.ssrc}>"


class FECPacket(_PacketCmpMixin):
    __slots__ = ("ssrc", "timestamp", "sequence")
    decrypted_data = b""

    def __init__(self, ssrc, timestamp, sequence):
        self.ssrc = ssrc
        self.timestamp = sequence
        self.sequence = timestamp

    def __repr__(self):
        return f"<FECPacket timestamp={self.timestamp} ssrc={self.ssrc} sequence={self.sequence}>"


# Consider adding silence attribute to differentiate (to skip isinstance)


class RTPPacket(_PacketCmpMixin):
    __slots__ = (
        "version",
        "padding",
        "extended",
        "cc",
        "marker",
        "payload",
        "sequence",
        "timestamp",
        "ssrc",
        "csrcs",
        "header",
        "data",
        "decrypted_data",
        "extension",
        "extension_data",
    )

    _hstruct = struct.Struct(">xxHII")
    _extension_header = Extension

    def __init__(self, data: bytes):
        data_arrays = bytearray(data)

        self.version: int = data_arrays[0] >> 6
        self.padding: bool = bool(data_arrays[0] & 0b00100000)
        self.extended: bool = bool(data_arrays[0] & 0b00010000)
        self.cc: int = data_arrays[0] & 0b00001111

        self.marker: bool = bool(data_arrays[1] & 0b10000000)
        self.payload: int = data_arrays[1] & 0b01111111

        seq, ts, ssrc = self._hstruct.unpack_from(data_arrays)

        self.sequence: int = seq
        self.timestamp: int = ts
        self.ssrc: int = ssrc

        self.csrcs = ()
        self.extension: Extension = None
        self.extension_data: Dict[int, bytes] = {}

        self.header: bytearray = data_arrays[:12]
        self.data: bytearray = data_arrays[12:]
        self.decrypted_data: Optional[bytes] = None

        if self.cc:
            fmt = f">{str(self.cc)}I"
            offset = struct.calcsize(fmt) + 12
            self.csrcs = struct.unpack(fmt, data[12:offset])
            self.data = data[offset:]

    def update_ext_headers(self, data: bytearray):
        """Adds extended header data to this packet, returns payload offset"""

        if not self.extended:
            return

        # data is the decrypted packet payload containing the extension header and opus data
        profile, length = struct.unpack_from(">2sH", data)

        if profile == b"\xBE\xDE":
            self._parse_bede_header(data, length)

        values = struct.unpack(">%sI" % length, data[4 : 4 + length * 4])
        self.extension = Extension(profile, length, values)

        return 4 + length * 4

    def _parse_bede_header(self, data: bytearray, length: int):
        offset = 4
        n = 0

        while n < length:
            next_byte = data[offset : offset + 1]

            if next_byte == b"\x00":
                offset += 1
                continue

            header = struct.unpack(">B", next_byte)[0]

            element_id = header >> 4
            element_len = 1 + (header & 0b0000_1111)

            self.extension_data[element_id] = data[offset + 1 : offset + 1 + element_len]
            offset += 1 + element_len
            n += 1

    def __repr__(self) -> str:
        _fields = (
            ("ext", self.extended),
            ("timestamp", self.timestamp),
            ("seq", self.sequence),
            ("ssrc", self.ssrc),
            ("size", len(self.data)),
        )
        return f"<RTPPacket {' '.join(f'{k}={repr(v)}' for k, v in _fields)}>"


class RTCPPacket(_PacketCmpMixin):
    __slots__ = ("version", "padding", "length")
    _header = struct.Struct(">BBH")
    _ssrc_fmt = struct.Struct(">I")
    type = None

    def __init__(self, data):
        head, _, self.length = self._header.unpack_from(data)
        self.version = head >> 6
        self.padding = bool(head & 0b00100000)
        # dubious, yet devious
        setattr(self, self.__slots__[0], head & 0b00011111)

    def __repr__(self):
        content = ", ".join("{}: {}".format(k, repr(getattr(self, k, None))) for k in self.__slots__)
        return "<{} {}>".format(self.__class__.__name__, content)

    @classmethod
    def from_data(cls, data):
        _, ptype, _ = cls._header.unpack_from(data)
        return _rtcp_map[ptype](data)


class SenderReportPacket(RTCPPacket):
    __slots__ = ("report_count", "ssrc", "info", "reports", "extension")
    _info_fmt = struct.Struct(">5I")
    _report_fmt = struct.Struct(">IB3x4I")
    _24bit_int_fmt = struct.Struct(">4xI")
    type = 200
    report_count: int

    def __init__(self, data):
        super().__init__(data)
        self.ssrc: int = self._ssrc_fmt.unpack_from(data, 4)[0]
        self.info: RRSenderInfo = self._read_sender_info(data, 8)

        reports = []
        for x in range(self.report_count):
            offset = 28 + 24 * x
            reports.append(self._read_report(data, offset))

        self.reports: Sequence[RReport] = tuple(reports)

        self.extension = None
        if len(data) > 28 + 24 * self.report_count:
            self.extension = data[28 + 24 * self.report_count :]

    def _read_sender_info(self, data: bytearray, offset: int):
        nhigh, nlow, rtp_ts, pcount, ocount = self._info_fmt.unpack_from(data, offset)
        ntotal = nhigh + _parse_low(nlow)
        return RRSenderInfo(ntotal, rtp_ts, pcount, ocount)

    def _read_report(self, data: bytearray, offset: int):
        ssrc, flost, seq, jit, lsr, dlsr = self._report_fmt.unpack_from(data, offset)
        clost = self._24bit_int_fmt.unpack_from(data, offset)[0] & 0xFFFFFF
        return RReport(ssrc, flost, clost, seq, jit, lsr, dlsr)


class ReceiverReportPacket(RTCPPacket):
    __slots__ = ("report_count", "ssrc", "reports", "extension")
    _report_fmt = struct.Struct(">IB3x4I")
    _24bit_int_fmt = struct.Struct(">4xI")
    type = 201

    def __init__(self, data):
        super().__init__(data)
        self.ssrc: int = self._ssrc_fmt.unpack_from(data, 4)[0]

        reports = []
        for x in range(self.report_count):
            offset = 8 + 24 * x
            reports.append(self._read_report(data, offset))

        self.reports: Sequence[RReport] = tuple(reports)

        self.extension = None
        if len(data) > 8 + 24 * self.report_count:
            self.extension = data[8 + 24 * self.report_count :]

    def _read_report(self, data, offset):
        ssrc, flost, seq, jit, lsr, dlsr = self._report_fmt.unpack_from(data, offset)
        clost = self._24bit_int_fmt.unpack_from(data, offset)[0] & 0xFFFFFF
        return RReport(ssrc, flost, clost, seq, jit, lsr, dlsr)


# http://www.rfcreader.com/#rfc3550_line2024
class SDESPacket(RTCPPacket):
    __slots__ = ("source_count", "chunks", "_pos")
    _item_header = struct.Struct(">BB")
    type = 202

    def __init__(self, data):
        super().__init__(data)
        _chunks = []
        self._pos: int = 4

        for x in range(self.source_count):
            _chunks.append(self._read_chunk(data))

        self.chunks: Sequence = tuple(_chunks)

    def _read_chunk(self, data: bytes):
        ssrc = self._ssrc_fmt.unpack_from(data, self._pos)[0]
        self._pos += 4

        # check for chunk with no items
        if data[self._pos : self._pos + 4] == b"\x00\x00\x00\x00":
            self._pos += 4
            return SDESChunk(ssrc, [])

        items = [self._read_item(data)]

        # Read items until END type is found
        while items[-1].type != 0:
            items.append(self._read_item(data))

        # pad chunk to 4 bytes
        if self._pos % 4:
            self._pos = ceil(self._pos / 4) * 4

        return SDESChunk(ssrc, items)

    def _read_item(self, data: bytes):
        itype, ilen = self._item_header.unpack_from(data, self._pos)
        self._pos += 2
        text = None

        if ilen:
            text = data[self._pos : self._pos + ilen].decode()
            self._pos += ilen

        return SDESItem(itype, ilen + 2, ilen, text)

    def _get_chunk_size(self, chunk: SDESChunk):
        return 4 + max(4, sum(i.size for i in chunk.items))  # + padding?


# http://www.rfcreader.com/#rfc3550_line2311
class BYEPacket(RTCPPacket):
    __slots__ = ("source_count", "ssrcs", "reason")
    type = 203

    def __init__(self, data):
        super().__init__(data)
        self.ssrcs = struct.unpack_from(">%sI" % self.source_count, data, 4)
        self.reason: Optional[str] = None

        body_length = 4 + len(self.ssrcs) * 4
        if len(data) > body_length:
            extra_len = struct.unpack_from("B", data, body_length)[0]
            reason = struct.unpack_from("%ss" % extra_len, data, body_length + 1)
            self.reason = reason.decode()


# http://www.rfcreader.com/#rfc3550_line2353
class APPPacket(RTCPPacket):
    __slots__ = ("subtype", "ssrc", "name", "data")
    _packet_info = struct.Struct(">I4s")
    type = 204

    def __init__(self, data):
        super().__init__(data)
        self.ssrc, name = self._packet_info.unpack_from(data, 4)
        self.name: str = name.decode("ascii")
        self.data = data[12:]  # should be a multiple of 32 bits but idc


_rtcp_map = {200: SenderReportPacket, 201: ReceiverReportPacket, 202: SDESPacket, 203: BYEPacket, 204: APPPacket}
