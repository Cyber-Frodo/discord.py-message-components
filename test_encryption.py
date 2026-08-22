"""Verify the RTP transport encryption without talking to Discord.

Encrypts a packet, splits it apart again and compares. Catches exactly the
mistakes that would otherwise only show up as noise in a voice channel:
a mis-sliced nonce, a forgotten CSRC list, the extension preamble ending up
in the wrong block.

Run from the repository root::

    py test_encryption.py
"""
import os
import struct
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `discord/__init__.py` pulls in the whole package, including `soundboard`,
# which needs `pydub` - a third-party dependency unrelated to voice. Rather
# than installing it, it is stubbed for the duration of this test: the point
# here is to verify the encryption, not the install environment.
for _name, _attrs in (('pydub', ('AudioSegment',)),):
    if _name not in sys.modules:
        _module = types.ModuleType(_name)
        for _attr in _attrs:
            setattr(_module, _attr, type(_attr, (), {}))
        sys.modules[_name] = _module

import nacl.secret
import nacl.utils

from discord.sink import RawData


class FakeClient:
    """Minimal stand-in for VoiceClient - only what RawData actually touches."""

    def __init__(self, mode: str, secret_key: bytes) -> None:
        self.mode = mode
        self.secret_key = list(secret_key)
        self._lite_nonce = 0

    # The real methods are reused unchanged so the test exercises production
    # code rather than a reimplementation of it.
    from discord.voice_client import VoiceClient as _VC
    _encrypt_aead_xchacha20_poly1305_rtpsize = _VC._encrypt_aead_xchacha20_poly1305_rtpsize
    _decrypt_aead_xchacha20_poly1305_rtpsize = _VC._decrypt_aead_xchacha20_poly1305_rtpsize
    checked_add = _VC.checked_add


def build_header(ssrc: int, sequence: int, timestamp: int, *,
                 extended: bool = False, cc: int = 0) -> bytearray:
    """Build an RTP header the way Discord sends it."""
    header = bytearray(12 + cc * 4)
    header[0] = 0x80 | (0x10 if extended else 0x00) | cc
    header[1] = 0x78
    struct.pack_into('>H', header, 2, sequence)
    struct.pack_into('>I', header, 4, timestamp)
    struct.pack_into('>I', header, 8, ssrc)
    for i in range(cc):
        struct.pack_into('>I', header, 12 + i * 4, 0xDEAD0000 + i)
    return header


def case_plain() -> bool:
    """Encrypt and decrypt again, no header extension."""
    key = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', key)

    opus = b'\xfc\xff\xfe' + bytes(range(120))
    header = build_header(0x11223344, 42, 960)

    packet = client._encrypt_aead_xchacha20_poly1305_rtpsize(bytes(header), opus)
    raw = RawData(packet, client)

    ok = raw.decrypted_data == opus
    print(f'  plain              : {"OK " if ok else "FAIL"}  '
          f'{len(opus)} B in, {len(raw.decrypted_data)} B out, '
          f'ssrc={raw.ssrc:#x}, seq={raw.sequence}')
    return ok


def case_extension() -> bool:
    """Packet WITH a header extension - where the split usually breaks.

    Discord sets the extension regularly. It is built by hand here because
    the library's own send path never produces one.
    """
    key = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', key)

    opus = b'\xfc\xff\xfe' + bytes(range(200))
    header = build_header(0x55667788, 7, 1920, extended=True)

    # Preamble: profile 0xBEDE followed by the length in 32-bit words.
    words = 2
    preamble = struct.pack('>HH', 0xBEDE, words)
    ext_data = bytes(range(words * 4))

    box = nacl.secret.Aead(key)
    nonce = bytearray(24)
    nonce[:4] = struct.pack('>I', 99)

    # AAD is header + preamble, ciphertext is extension data + Opus.
    aad = bytes(header) + preamble
    ciphertext = box.encrypt(ext_data + opus, aad, bytes(nonce)).ciphertext
    packet = aad + ciphertext + bytes(nonce[:4])

    raw = RawData(packet, client)

    ok = raw.decrypted_data == opus
    print(f'  with extension     : {"OK " if ok else "FAIL"}  '
          f'{len(opus)} B in, {len(raw.decrypted_data)} B out, '
          f'ext_offset={raw.ext_offset}, extended={raw.extended}')
    if not ok:
        print(f'      expected: {opus[:16].hex()}')
        print(f'      got     : {bytes(raw.decrypted_data[:16]).hex()}')
    return ok


def case_csrc() -> bool:
    """Packet with a CSRC list - rarer, but the split has to hold."""
    key = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', key)

    opus = bytes(range(60))
    header = build_header(0x99AABBCC, 3, 2880, cc=2)

    box = nacl.secret.Aead(key)
    nonce = bytearray(24)
    nonce[:4] = struct.pack('>I', 5)
    ciphertext = box.encrypt(opus, bytes(header), bytes(nonce)).ciphertext
    packet = bytes(header) + ciphertext + bytes(nonce[:4])

    raw = RawData(packet, client)
    ok = raw.decrypted_data == opus
    print(f'  with CSRC list     : {"OK " if ok else "FAIL"}  '
          f'cc={raw.cc}, header {len(raw.header)} B')
    return ok


def case_interleaved() -> bool:
    """Two speakers interleaved - catches a nonce cached on the client.

    If the nonce were stored on the client instead of read from the packet,
    this case would come out as noise.
    """
    key = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', key)

    packets = []
    expected = []
    for i in range(6):
        opus = bytes([i]) * (50 + i)
        header = build_header(0x1000 + (i % 2), i, i * 960)
        packets.append(client._encrypt_aead_xchacha20_poly1305_rtpsize(bytes(header), opus))
        expected.append(opus)

    # Deliberately decrypt out of order.
    order = [3, 0, 5, 1, 4, 2]
    ok = all(RawData(packets[i], client).decrypted_data == expected[i] for i in order)
    print(f'  shuffled order     : {"OK " if ok else "FAIL"}  '
          f'6 packets, order {order}')
    return ok


def main() -> None:
    print('Testing aead_xchacha20_poly1305_rtpsize against production code:')
    results = [case_plain(), case_extension(), case_csrc(), case_interleaved()]
    passed = sum(results)
    print(f'--- {passed} of {len(results)} passed')
    sys.exit(0 if passed == len(results) else 1)


if __name__ == '__main__':
    main()
