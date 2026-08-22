# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-2021 Rapptz & (c) 2021-present mccoderpy

Implementation of voice-receiving was taken from PyCord

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

"""Some documentation to refer to:

- Our main web socket (mWS) sends opcode 4 with a guild ID and channel ID.
- The mWS receives VOICE_STATE_UPDATE and VOICE_SERVER_UPDATE.
- We pull the session_id from VOICE_STATE_UPDATE.
- We pull the token, endpoint and server_id from VOICE_SERVER_UPDATE.
- Then we initiate the voice web socket (vWS) pointing to the endpoint.
- We send opcode 0 with the user_id, server_id, session_id and token using the vWS.
- The vWS sends back opcode 2 with an ssrc, port, modes(array) and hearbeat_interval.
- We send a UDP discovery packet to endpoint:port and receive our IP and our port in LE.
- Then we send our IP and port via vWS with opcode 1.
- When that's all done, we receive opcode 4 from the vWS.
- Finally we can transmit data to endpoint:port.
"""

import asyncio
import socket
import logging
import struct
import threading
import select
import time

from typing import (
    Any,
    Callable,
    List,
    Optional,
    TYPE_CHECKING,
    Tuple
)

if TYPE_CHECKING:
    from .types.voice import (
        VoiceRegion as VoiceRegionData,
    )

from . import opus, utils
from .backoff import ExponentialBackoff
from .gateway import *
from .errors import ClientException, ConnectionClosed, RecordingException
from .player import AudioPlayer, AudioSource
from .sink import Sink, RawData

try:
    import nacl.secret
    has_nacl = True
except ImportError:
    has_nacl = False

# DAVE (Discord Audio & Video End-to-End Encryption) has been mandatory for
# every non-stage voice channel since 2026-03-02. Without it the voice
# gateway rejects the connection with close code 4017, before a single audio
# packet is sent.
#
# The import is deliberately optional: anyone using this library for text
# commands only should not be forced to install it. When it is missing, the
# failure happens at connect time - with a message that says what to do.
try:
    import davey
    has_dave = True
except ImportError:
    has_dave = False

log = logging.getLogger(__name__)

__all__ = (
    'VoiceRegionInfo',
    'VoiceClient',
    'VoiceProtocol',
)


class VoiceRegionInfo:
    """A class containing info about a specific voice region.

    These can be retrieved via :meth:`~discord.Client.fetch_voice_regions`.

    .. versionadded:: 2.0

    Attributes
    ------------
    id: :class:`str`
        The unique ID of the region.
    name: :class:`str`
        The name of the region.
    vip: :class:`bool`
        Indicates if this is a VIP-only server.
    optimal: :class:`bool`
    	``True`` for a single server that is closest to the current user's client
    deprecated: :class:`bool`
        Indicates if this is a deprecated voice region (avoid switching to these).
    custom: :class:`bool`
        Indicates if this is a custom voice region (used for events/etc).

    .. container:: operations

        .. describe:: x == y
            Whether two voice regions are equal.
        .. describe:: x != y
            Whether two voice regions are not equal.
        .. describe:: x > y
            Whether a voice region is optimal over another.
        .. describe:: x < y
            Whether a voice region is not optimal over another.
        .. describe:: str(x)
            Returns the id of the region.
        .. describe:: repr(x)
            Returns a representation of the region.
        ..
    """
    def __init__(self, *, data: VoiceRegionData) -> None:
        self.id: str = data['id']
        self.name: str = data['name']
        self.vip: bool = data['vip']
        self.optimal: bool = data['optimal']
        self.deprecated: bool = data['deprecated']
        self.custom: bool = data['custom']

    def __repr__(self) -> str:
        return f'<VoiceRegion id={self.id} name={self.name!r} vip={self.vip} optimal={self.optimal}' \
               f' deprecated={self.deprecated} custom={self.custom}>'

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, VoiceRegionInfo) and other.id == self.id

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: Any) -> bool:
        return isinstance(other, VoiceRegionInfo) and self.optimal and not other.optimal

    def __ge__(self, other: Any) -> bool:
        return isinstance(other, VoiceRegionInfo) and self.optimal and not other.optimal

    def __lt__(self, other: Any) -> bool:
        return isinstance(other, VoiceRegionInfo) and not self.optimal and other.optimal

    def __le__(self, other: Any) -> bool:
        return isinstance(other, VoiceRegionInfo) and not self.optimal and other.optimal

    def __str__(self) -> str:
        return self.id


class VoiceProtocol:
    """A class that represents the Discord voice protocol.

    This is an abstract class. The library provides a concrete implementation
    under :class:`VoiceClient`.

    This class allows you to implement a protocol to allow for an external
    method of sending voice, such as Lavalink_ or a native library implementation.

    These classes are passed to :meth:`abc.Connectable.connect`.

    .. _Lavalink: https://github.com/freyacodes/Lavalink

    Parameters
    ------------
    client: :class:`Client`
        The client (or its subclasses) that started the connection request.
    channel: :class:`abc.Connectable`
        The voice channel that is being connected to.
    """

    def __init__(self, client, channel):
        self.client = client
        self.channel = channel

    async def on_voice_state_update(self, data):
        """|coro|

        An abstract method that is called when the client's voice state
        has changed. This corresponds to ``VOICE_STATE_UPDATE``.

        Parameters
        ------------
        data: :class:`dict`
            The raw `voice state payload`__.

            .. _voice_state_update_payload: https://discord.com/developers/docs/resources/voice#voice-state-object

            __ voice_state_update_payload_
        """
        raise NotImplementedError

    async def on_voice_server_update(self, data):
        """|coro|

        An abstract method that is called when initially connecting to voice.
        This corresponds to ``VOICE_SERVER_UPDATE``.

        Parameters
        ------------
        data: :class:`dict`
            The raw `voice server update payload`__.

            .. _voice_server_update_payload: https://discord.com/developers/docs/topics/gateway#voice-server-update-voice-server-update-event-fields

            __ voice_server_update_payload_
        """
        raise NotImplementedError

    async def connect(self, *, timeout, reconnect):
        """|coro|

        An abstract method called when the client initiates the connection request.

        When a connection is requested initially, the library calls the constructor
        under ``__init__`` and then calls :meth:`connect`. If :meth:`connect` fails at
        some point then :meth:`disconnect` is called.

        Within this method, to start the voice connection flow it is recommended to
        use :meth:`Guild.change_voice_state` to start the flow. After which,
        :meth:`on_voice_server_update` and :meth:`on_voice_state_update` will be called.
        The order that these two are called is unspecified.

        Parameters
        ------------
        timeout: :class:`float`
            The timeout for the connection.
        reconnect: :class:`bool`
            Whether reconnection is expected.
        """
        raise NotImplementedError

    async def disconnect(self, *, force):
        """|coro|

        An abstract method called when the client terminates the connection.

        See :meth:`cleanup`.

        Parameters
        ------------
        force: :class:`bool`
            Whether the disconnection was forced.
        """
        raise NotImplementedError

    def cleanup(self):
        """This method *must* be called to ensure proper clean-up during a disconnect.

        It is advisable to call this from within :meth:`disconnect` when you are
        completely done with the voice protocol instance.

        This method removes it from the internal state cache that keeps track of
        currently alive voice clients. Failure to clean-up will cause subsequent
        connections to report that it's still connected.
        """
        key_id, _ = self.channel._get_voice_client_key()
        self.client._connection._remove_voice_client(key_id)

class VoiceClient(VoiceProtocol):
    """Represents a Discord voice connection.

    You do not create these, you typically get them from
    e.g. :meth:`VoiceChannel.connect`.

    Warning
    --------
    In order to use PCM based AudioSources, you must have the opus library
    installed on your system and loaded through :func:`opus.load_opus`.
    Otherwise, your AudioSources must be opus encoded (e.g. using :class:`FFmpegOpusAudio`)
    or the library will not be able to transmit audio.

    Attributes
    -----------
    session_id: :class:`str`
        The voice connection _session ID.
    token: :class:`str`
        The voice connection token.
    endpoint: :class:`str`
        The endpoint we are connecting to.
    channel: :class:`abc.Connectable`
        The voice channel connected to.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop that the voice client is running on.
    """
    def __init__(self, client, channel):
        if not has_nacl:
            raise RuntimeError("PyNaCl library needed in order to use voice")

        super().__init__(client, channel)
        state = client._connection
        self.token = None
        self.socket = None
        self.loop = state.loop
        self._state = state
        # this will be used in the AudioPlayer thread
        self._connected = threading.Event()

        self._handshaking = False
        self._potentially_reconnecting = False
        self._voice_state_complete = asyncio.Event()
        self._voice_server_complete = asyncio.Event()

        self.mode = None
        self._connections = 0
        self.sequence = 0
        self.timestamp = 0
        self._runner = None
        self._player = None
        self.encoder = None
        self.decoder = None
        self._lite_nonce = 0
        self.ws: DiscordVoiceWebSocket = None

        # --- DAVE ---
        # `dave_session` stays None while Discord has not negotiated a DAVE
        # version (stage channels). Everything else checks against it.
        self.dave_session = None
        self.dave_protocol_version = 0
        # Transitions announced but not yet executed:
        # {transition_id: protocol_version}
        self.dave_pending_transitions = {}

        self.paused = False
        self.recording = False
        self.user_timestamps = {}
        self.sink = None
        self.starting_time = None
        self.stopping_time = None

    warn_nacl = not has_nacl
    warn_dave = not has_dave
    # NOTE: the order matters. Discord offers a list of modes in
    # `initial_connection`; we pick the first entry that also appears here,
    # so the current mode has to come first.
    #
    # Discord removed the three `xsalsa20` variants on 2024-11-18. They are
    # kept only as a fallback in case a server still offers them, which no
    # longer happens in practice. Before that date they were the normal case
    # - which is exactly why `recv_audio()` used to work and then stopped,
    # without anything changing in this library.
    supported_modes = (
        'aead_xchacha20_poly1305_rtpsize',
        'xsalsa20_poly1305_lite',
        'xsalsa20_poly1305_suffix',
        'xsalsa20_poly1305',
    )

    @property
    def guild(self):
        """Optional[:class:`Guild`]: The guild we're connected to, if applicable."""
        return getattr(self.channel, 'guild', None)

    @property
    def user(self):
        """:class:`ClientUser`: The user connected to voice (i.e. ourselves)."""
        return self._state.user

    def checked_add(self, attr, value, limit):
        val = getattr(self, attr)
        if val + value > limit:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, val + value)

    # connection related

    async def on_voice_state_update(self, data):
        self.session_id = data['session_id']
        channel_id = data['channel_id']

        if not self._handshaking or self._potentially_reconnecting:
            # If we're done handshaking then we just need to update ourselves
            # If we're potentially reconnecting due to a 4014, then we need to differentiate
            # a channel move and an actual force disconnect
            if channel_id is None:
                # We're being disconnected so cleanup
                await self.disconnect()
            else:
                guild = self.guild
                self.channel = channel_id and guild and guild.get_channel(int(channel_id))
        else:
            self._voice_state_complete.set()

    async def on_voice_server_update(self, data):
        if self._voice_server_complete.is_set():
            log.info('Ignoring extraneous voice server update.')
            return

        self.token = data.get('token')
        self.server_id = int(data['guild_id'])
        endpoint = data.get('endpoint')

        if endpoint is None or self.token is None:
            log.warning('Awaiting endpoint... This requires waiting. ' \
                        'If timeout occurred considering raising the timeout and reconnecting.')
            return

        self.endpoint, _, _ = endpoint.rpartition(':')
        if self.endpoint.startswith('wss://'):
            # Just in case, strip it off since we're going to add it later
            self.endpoint = self.endpoint[6:]

        # This gets set later
        self.endpoint_ip = None

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)

        if not self._handshaking:
            # If we're not handshaking then we need to terminate our previous connection in the websocket
            await self.ws.close(4000)
            return

        self._voice_server_complete.set()

    async def voice_connect(self):
        await self.channel.guild.change_voice_state(channel=self.channel)

    async def voice_disconnect(self):
        log.info('The voice handshake is being terminated for Channel ID %s (Guild ID %s)', self.channel.id, self.guild.id)
        await self.channel.guild.change_voice_state(channel=None)

    def prepare_handshake(self):
        self._voice_state_complete.clear()
        self._voice_server_complete.clear()
        self._handshaking = True
        log.info('Starting voice handshake... (connection attempt %d)', self._connections + 1)
        self._connections += 1

    def finish_handshake(self):
        log.info('Voice handshake complete. Endpoint found %s', self.endpoint)
        self._handshaking = False
        self._voice_server_complete.clear()
        self._voice_state_complete.clear()

    async def connect_websocket(self):
        ws = await DiscordVoiceWebSocket.from_client(self)
        self._connected.clear()
        while ws.secret_key is None:
            await ws.poll_event()
        self._connected.set()
        return ws

    async def connect(self, *, reconnect, timeout):
        log.info('Connecting to voice...')
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
                    log.exception('Failed to connect to voice... Retrying...')
                    await asyncio.sleep(1 + i * 2.0)
                    await self.voice_disconnect()
                    continue
                else:
                    raise

        if self._runner is None:
            self._runner = self.loop.create_task(self.poll_voice_ws(reconnect))

    async def potential_reconnect(self):
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
    def latency(self):
        """:class:`float`: Latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds.

        This could be referred to as the Discord Voice WebSocket latency and is
        an analogue of user's voice latencies as seen in the Discord client.

        .. versionadded:: 1.4
        """
        ws = self.ws
        return float("inf") if not ws else ws.latency

    @property
    def average_latency(self):
        """:class:`float`: Average of most recent 20 HEARTBEAT latencies in seconds.

        .. versionadded:: 1.4
        """
        ws = self.ws
        return float("inf") if not ws else ws.average_latency

    async def poll_voice_ws(self, reconnect):
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
                        log.info('Disconnecting from voice normally, close code %d.', exc.code)
                        await self.disconnect()
                        break
                    if exc.code == 4014:
                        log.info('Disconnected from voice by force... potentially reconnecting.')
                        successful = await self.potential_reconnect()
                        if not successful:
                            log.info('Reconnect was unsuccessful, disconnecting from voice normally...')
                            await self.disconnect()
                            break
                        else:
                            continue

                if not reconnect:
                    await self.disconnect()
                    raise

                retry = backoff.delay()
                log.exception('Disconnected from voice... Reconnecting in %.2fs.', retry)
                self._connected.clear()
                await asyncio.sleep(retry)
                await self.voice_disconnect()
                try:
                    await self.connect(reconnect=True, timeout=self.timeout)
                except asyncio.TimeoutError:
                    # at this point we've retried 5 times... let's continue the loop.
                    log.warning('Could not connect to voice... Retrying...')
                    continue

    async def disconnect(self, *, force=False):
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

    async def move_to(self, channel):
        """|coro|

        Moves you to a different voice channel.

        Parameters
        -----------
        channel: :class:`abc.Snowflake`
            The channel to move to. Must be a voice channel.
        """
        await self.channel.guild.change_voice_state(channel=channel)

    def is_connected(self):
        """Indicates if the voice client is connected to voice."""
        return self._connected.is_set()

    # audio related

    def _get_voice_packet(self, data):
        header = bytearray(12)

        # Formulate rtp header
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into('>H', header, 2, self.sequence)
        struct.pack_into('>I', header, 4, self.timestamp)
        struct.pack_into('>I', header, 8, self.ssrc)

        # --- DAVE: end-to-end layer goes first ---
        # Mirrors the receive path: DAVE inside, transport outside. Discord
        # encrypts every Opus frame individually with the sender's own key;
        # the transport layer is applied on top of that.
        if self.dave_session is not None and self.dave_protocol_version > 0:
            data = self.dave_session.encrypt_opus(bytes(data))

        encrypt_packet = getattr(self, '_encrypt_' + self.mode)
        return encrypt_packet(header, data)

    def _encrypt_aead_xchacha20_poly1305_rtpsize(self, header, data):
        """Encrypt a packet using ``aead_xchacha20_poly1305_rtpsize``.

        The mandatory transport mode since 2024-11-18, alongside the optional
        ``aead_aes256_gcm_rtpsize``.

        Layout of the resulting packet::

            [ RTP header 12 B ][ ciphertext + Poly1305 tag ][ nonce 4 B ]

        The RTP header is passed as **additional authenticated data**: it
        stays readable but is protected against tampering. That is what
        separates this mode from ``_lite``.

        :param header: the 12-byte RTP header, also used as AAD.
        :param data: the Opus payload to encrypt.
        :return: the packet ready to be sent, as ``bytes``.
        """
        box = nacl.secret.Aead(bytes(self.secret_key))
        nonce = bytearray(24)

        # Only the first 4 bytes of the nonce are transmitted, the rest stays
        # zero. The counter wraps at 2^32-1 - `checked_add` resets it instead
        # of raising.
        nonce[:4] = struct.pack('>I', self._lite_nonce)
        self.checked_add('_lite_nonce', 1, 4294967295)

        return header + box.encrypt(bytes(data), bytes(header), bytes(nonce)).ciphertext + nonce[:4]

    def _decrypt_aead_xchacha20_poly1305_rtpsize(self, header, data):
        """Decrypt a packet encrypted with ``aead_xchacha20_poly1305_rtpsize``.

        Counterpart to :meth:`_encrypt_aead_xchacha20_poly1305_rtpsize`.

        .. warning::

            The nonce sits at the end of ``data`` and is stripped here. It
            must **not** be cached on the client: ``recv_audio()`` runs on its
            own thread and handles packets from multiple speakers, so a nonce
            attribute would be a race condition surfacing as intermittent
            noise - effectively impossible to track down.

        .. warning::

            The CSRC list and the extension preamble have already been handled
            by ``RawData``. With ``_rtpsize`` modes the 4-byte preamble belongs
            to the AAD and **not** to the ciphertext. Getting this wrong either
            fails the authentication tag or yields noise.

        :param header: RTP header including the extension preamble (the AAD).
        :param data: ciphertext **with** the 4-byte nonce still appended.
        :return: the decrypted payload.
        :raises nacl.exceptions.CryptoError: when the tag does not verify -
            almost always a sign that header or nonce were split incorrectly.
        """
        box = nacl.secret.Aead(bytes(self.secret_key))
        nonce = bytearray(24)
        nonce[:4] = data[-4:]

        return box.decrypt(bytes(data[:-4]), bytes(header), bytes(nonce))

    def _encrypt_xsalsa20_poly1305(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        nonce = bytearray(24)
        nonce[:12] = header

        return header + box.encrypt(bytes(data), bytes(nonce)).ciphertext

    def _encrypt_xsalsa20_poly1305_suffix(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)

        return header + box.encrypt(bytes(data), nonce).ciphertext + nonce

    def _encrypt_xsalsa20_poly1305_lite(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        nonce = bytearray(24)

        nonce[:4] = struct.pack('>I', self._lite_nonce)
        self.checked_add('_lite_nonce', 1, 4294967295)

        return header + box.encrypt(bytes(data), bytes(nonce)).ciphertext + nonce[:4]

    def _decrypt_xsalsa20_poly1305(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))

        nonce = bytearray(24)
        nonce[:12] = header

        return self.strip_header_ext(box.decrypt(bytes(data), bytes(nonce)))

    def _decrypt_xsalsa20_poly1305_suffix(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))

        nonce_size = nacl.secret.SecretBox.NONCE_SIZE
        nonce = data[-nonce_size:]

        return self.strip_header_ext(box.decrypt(bytes(data[:-nonce_size]), nonce))

    def _decrypt_xsalsa20_poly1305_lite(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))

        nonce = bytearray(24)
        nonce[:4] = data[-4:]
        data = data[:-4]

        return self.strip_header_ext(box.decrypt(bytes(data), bytes(nonce)))

    @property
    def max_dave_protocol_version(self) -> int:
        """Highest DAVE version this client can speak.

        0 means "no DAVE". Since 2026-03-02 Discord rejects such connections
        with close code 4017 - except in stage channels.
        """
        return davey.DAVE_PROTOCOL_VERSION if has_dave else 0

    async def reinit_dave_session(self) -> None:
        """Set up the DAVE session from scratch.

        Called on every epoch change and after a rejected commit. An existing
        session is reused and only reset, which avoids rebuilding the signing
        key pair.

        :raises RuntimeError: when ``davey`` is missing although DAVE was
            negotiated. The message names the install command, because a bare
            ``ImportError`` explains nothing at this point.
        """
        if not has_dave:
            raise RuntimeError(
                'Voice channels require the "davey" package '
                '(Discord has mandated DAVE since 2026-03-02). '
                'Install it with: py -m pip install davey'
            )

        channel_id = self.channel.id if self.channel else 0
        if self.dave_session is None:
            self.dave_session = davey.DaveSession(
                self.dave_protocol_version, self.user.id, channel_id
            )
        else:
            self.dave_session.reinit(
                self.dave_protocol_version, self.user.id, channel_id
            )
        log.debug('DAVE session established (version %d, channel %s)',
                  self.dave_protocol_version, channel_id)

    def _execute_transition(self, transition_id: int) -> None:
        """Apply a previously announced transition.

        .. warning::

            Version 0 means falling back to "no DAVE". Passthrough mode has to
            be enabled in that case, otherwise the decryptor keeps trying to
            decrypt and discards every packet - the connection stays up and is
            silent anyway.

        :param transition_id: the id from the announcement.
        """
        version = self.dave_pending_transitions.pop(transition_id, None)
        if version is None:
            log.debug('Transition %d was never announced - ignored', transition_id)
            return

        self.dave_protocol_version = version
        if self.dave_session is not None:
            self.dave_session.set_passthrough_mode(version == 0, 120)
        log.debug('DAVE transition %d executed, version is now %d', transition_id, version)

    @staticmethod
    def strip_header_ext(data):
        if data[0] == 0xBE and data[1] == 0xDE and len(data) > 4:
            _, length = struct.unpack_from(">HH", data)
            offset = 4 + length * 4
            data = data[offset:]
        return data

    def get_ssrc(self, user_id):
        return {info["user_id"]: ssrc for ssrc, info in self.ws.ssrc_map.items()}[
            user_id
        ]

    def play(
            self, source: AudioSource, *, after: Callable[[Optional[Exception]], Any] = None
    ) -> None:
        """Plays an :class:`AudioSource`.

        The finalizer, ``after`` is called after the source has been exhausted
        or an error occurred.

        If an error happens while the audio player is running, the exception is
        caught and the audio player is then stopped.  If no after callback is
        passed, any caught exception will be displayed as if it were raised.

        Parameters
        -----------
        source: :class:`AudioSource`
            The audio source we're reading from.
        after: Callable[[:class:`Exception`], Any]
            The finalizer that is called after the stream is exhausted.
            This function must have a single parameter, ``error``, that
            denotes an optional exception that was raised during playing.

        Raises
        -------
        ClientException
            Already playing audio or not connected.
        TypeError
            Source is not a :class:`AudioSource` or after is not a callable.
        OpusNotLoaded
            Source is not opus encoded and opus is not loaded.
        """

        if not self.is_connected():
            raise ClientException('Not connected to voice.')

        if self.is_playing():
            raise ClientException('Already playing audio.')

        if not isinstance(source, AudioSource):
            raise TypeError('source must an AudioSource not {0.__class__.__name__}'.format(source))

        if not self.encoder and not source.is_opus():
            self.encoder = opus.Encoder()

        self._player = AudioPlayer(source, self, after=after)
        self._player.start()

    def is_playing(self):
        """Indicates if we're currently playing audio."""
        return self._player is not None and self._player.is_playing()

    def is_paused(self):
        """Indicates if we're playing audio, but if we're paused."""
        return self._player is not None and self._player.is_paused()

    def stop(self):
        """Stops playing audio."""
        if self._player:
            self._player.stop()
            self._player = None

    def pause(self):
        """Pauses the audio playing."""
        if self._player:
            self._player.pause()

    def resume(self):
        """Resumes the audio playing."""
        if self._player:
            self._player.resume()

    @property
    def source(self):
        """Optional[:class:`AudioSource`]: The audio source being played, if playing.

        This property can also be used to change the audio source currently being played.
        """
        return self._player.source if self._player else None

    @source.setter
    def source(self, value):
        if not isinstance(value, AudioSource):
            raise TypeError('expected AudioSource not {0.__class__.__name__}.'.format(value))

        if self._player is None:
            raise ValueError('Not playing anything.')

        self._player._set_source(value)

    def send_audio_packet(self, data, *, encode=True):
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
            encoded_data = self.encoder.encode(data, self.encoder.SAMPLES_PER_FRAME)
        else:
            encoded_data = data
        packet = self._get_voice_packet(encoded_data)
        try:
            self.socket.sendto(packet, (self.endpoint_ip, self.voice_port))
        except BlockingIOError:
            log.warning('A packet has been dropped (seq: %s, timestamp: %s)', self.sequence, self.timestamp)

        self.checked_add('timestamp', opus.Encoder.SAMPLES_PER_FRAME, 4294967295)

    def unpack_audio(self, data):
        """Takes an audio packet received from Discord and decodes it into pcm audio data.
        If there are no users talking in the channel, `None` will be returned.
        You must be connected to receive audio.
        Parameters
        ---------
        data: :class:`bytes`
            Bytes received by Discord via the UDP connection used for sending and receiving voice data.
        """
        if 200 <= data[1] <= 204:
            # RTCP received.
            # RTCP provides information about the connection
            # as opposed to actual audio data, so it's not
            # important at the moment.
            return
        if self.paused:
            return

        data = RawData(data, self)

        if data.decrypted_data == b'\xf8\xff\xfe':  # Frame of silence
            return

        # --- DAVE: unwrap the second layer ---
        # The order is mandatory: transport first (done in RawData), then
        # DAVE, then Opus. Swapping the two layers yields data that decrypts
        # cleanly and still sounds like noise.
        #
        # NOTE: `decrypt()` needs the *user id*, not the SSRC. The mapping
        # comes from `ssrc_map`, populated by the gateway's SPEAKING events.
        # While it is still empty a packet cannot be attributed and is
        # dropped - which only happens in the first moments, before anyone
        # has spoken.
        if self.dave_session is not None and self.dave_protocol_version > 0:
            entry = self.ws.ssrc_map.get(data.ssrc)
            if entry is None:
                log.debug('Dropped packet with unknown SSRC %s', data.ssrc)
                return
            try:
                data.decrypted_data = self.dave_session.decrypt(
                    entry['user_id'], davey.MediaType.audio, bytes(data.decrypted_data)
                )
            except Exception:
                # During an epoch change individual packets can be
                # undecryptable. That is expected and must not tear down the
                # receive loop - but it is logged, otherwise a permanent
                # failure stays invisible.
                log.debug('DAVE decryption failed (SSRC %s)',
                          data.ssrc, exc_info=True)
                return
            if not data.decrypted_data:
                return

        self.decoder.decode(data)

    def start_recording(self, sink, callback, *args):
        """The bot will begin recording audio from the current voice channel it is in.
        This function uses a thread so the current code line will not be stopped.
        Must be in a voice channel to use.
        Must not be already recording.
        Parameters
        ----------
        sink: :class:`Sink`
            A Sink which will "store" all the audio data.
        callback: :class:`asynchronous function`
            A function which is called after the bot has stopped recording.
        *args:
            Args which will be passed to the callback function.
        Raises
        ------
        RecordingException
            Not connected to a voice channel.
        RecordingException
            Already recording.
        RecordingException
            Must provide a Sink object.
        """
        if not self.is_connected():
            raise RecordingException('Not connected to voice channel.')
        if self.recording:
            raise RecordingException("Already recording.")
        if not isinstance(sink, Sink):
            raise RecordingException("Must provide a Sink object.")

        self.empty_socket()

        self.decoder = opus.DecodeManager(self)
        self.decoder.start()
        self.recording = True
        self.sink = sink
        sink.init(self)

        t = threading.Thread(target=self.recv_audio, args=(sink, callback, *args,))
        t.start()

    def stop_recording(self):
        """Stops the recording.
        Must be already recording.
        Raises
        ------
        RecordingException
            Not currently recording.
        """
        if not self.recording:
            raise RecordingException("Not currently recording audio.")
        self.decoder.stop()
        self.recording = False
        self.paused = False

    def toggle_pause(self):
        """Pauses or unpauses the recording.
        Must be already recording.
        Raises
        ------
        RecordingException
            Not currently recording.
         """
        if not self.recording:
            raise RecordingException("Not currently recording audio.")
        self.paused = not self.paused

    def empty_socket(self):
        while True:
            ready, _, _ = select.select([self.socket], [], [], 0.0)
            if not ready:
                break
            for s in ready:
                s.recv(4096)

    def recv_audio(self, sink, callback, *args):
        #  Gets data from _recv_audio and sorts
        #  it by user, handles pcm files and
        #  silence that should be added.

        self.user_timestamps = {}
        self.starting_time = time.perf_counter()
        while self.recording:
            ready, _, err = select.select([self.socket], [],
                                          [self.socket], 0.01)
            if not ready:
                if err:
                    print(f"Socket error: {err}")
                continue

            try:
                data = self.socket.recv(4096)
            except OSError:
                self.stop_recording()
                continue

            self.unpack_audio(data)

        self.stopping_time = time.perf_counter()
        self.sink.cleanup()
        callback = asyncio.run_coroutine_threadsafe(callback(self.sink, *args), self.loop)
        result = callback.result()

        if result is not None:
            print(result)

    def recv_decoded_audio(self, data):
        if data.ssrc not in self.user_timestamps:
            self.user_timestamps.update({data.ssrc: data.timestamp})
            # Add silence of when they were not being recorded.
            data.decoded_data = struct.pack('<h', 0) * round(
                self.decoder.CHANNELS * self.decoder.SAMPLING_RATE * (time.perf_counter() - self.starting_time)
            ) + data.decoded_data
        else:
            self.user_timestamps[data.ssrc] = data.timestamp

        silence = data.timestamp - self.user_timestamps[data.ssrc] - 960
        data.decoded_data = struct.pack('<h', 0) * silence + data.decoded_data
        while data.ssrc not in self.ws.ssrc_map:
            time.sleep(0.05)
        self.sink.write(data.decoded_data, self.ws.ssrc_map[data.ssrc]['user_id'])