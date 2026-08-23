"""Verify voice receiving against live Discord - the only hard proof.

The encryption itself can be checked at a desk (`test_encryption.py`), the
connection cannot: DAVE negotiates an MLS group with Discord's servers, and
whether that succeeds only shows in a real voice channel.

What it does:
    1. Log in, join the given voice channel
    2. Record for DURATION seconds
    3. Write one WAV file per speaker and report its size

Usage (Git Bash or PowerShell)::

    py -m pip install "davey>=0.1.6" "PyNaCl>=1.5.0,<1.6"
    export DISCORD_TOKEN=...      # PowerShell: $env:DISCORD_TOKEN = '...'
    py test_voice_receive.py <voice-channel-id>

The proof is **not** "no errors in the log" but a WAV file you can hear
yourself in. A 44-byte file is an empty WAV header - nothing arrived.
"""
import asyncio
import os
import sys
import time

import discord

DURATION = 15  # seconds to record


def timestamp() -> str:
    return time.strftime('%H:%M:%S')


def report(text: str) -> None:
    print(f'[{timestamp()}] {text}', flush=True)


class ProbeBot(discord.Client):
    """Minimal client that performs exactly one recording and exits."""

    def __init__(self, channel_id: int) -> None:
        intents = discord.Intents.default()
        intents.voice_states = True
        super().__init__(intents=intents)
        self.channel_id = channel_id
        self.finished = asyncio.Event()

    async def on_ready(self) -> None:
        report(f'Logged in as {self.user} (id {self.user.id})')

        channel = self.get_channel(self.channel_id)
        if channel is None:
            report(f'ERROR: channel {self.channel_id} not found - is the bot on that guild?')
            self.finished.set()
            return
        if not isinstance(channel, discord.VoiceChannel):
            report(f'ERROR: {channel.name} is not a voice channel but {type(channel).__name__}')
            self.finished.set()
            return

        report(f'Joining voice channel "{channel.name}"')
        try:
            vc = await channel.connect()
        except Exception as error:
            report(f'ERROR while connecting: {type(error).__name__}: {error}')
            report('  Close code 4017 means DAVE is missing or was not negotiated.')
            self.finished.set()
            return

        report(f'Connected. Transport mode: {vc.mode}')
        report(f'DAVE protocol version: {vc.dave_protocol_version} '
               f'(0 = no DAVE, i.e. a stage channel)')
        report(f'DAVE session: {"present" if vc.dave_session is not None else "none"}')
        if vc.dave_session is not None:
            report(f'  status: {vc.dave_session.status}, ready: {vc.dave_session.ready}')
            report(f'  voice privacy code: {vc.dave_session.voice_privacy_code}')

        report(f'Recording for {DURATION} s - **speak now**')
        # Sink API of this fork: encoding and output path on the constructor,
        # not a separate class per format (that is py-cord).
        vc.start_recording(discord.Sink(encoding='wav', output_path='.'),
                           self._on_finished)

        await asyncio.sleep(DURATION)
        vc.stop_recording()
        await asyncio.sleep(1)
        await vc.disconnect()
        self.finished.set()

    async def _on_finished(self, sink, *args) -> None:
        """Called after `stop_recording` with whatever was captured."""
        report(f'Recording finished - {len(sink.audio_data)} speaker(s) captured')

        if not sink.audio_data:
            report('  NO AUDIO. Possible causes:')
            report('   - nobody spoke')
            report('   - the SSRC map is empty (no "speaking" event was sent)')
            report('   - DAVE decryption fails (enable DEBUG logging to see)')
            return

        for user_id, audio in sink.audio_data.items():
            # After `cleanup` the `file` attribute holds the path of the
            # finished file rather than an open file object.
            path = audio.file if isinstance(audio.file, str) else getattr(audio.file, 'name', None)
            if not path or not os.path.exists(path):
                report(f'  user {user_id}: no file was produced')
                continue

            size = os.path.getsize(path)
            # A bare WAV header is 44 bytes - anything at or below that means
            # not a single audio frame arrived.
            verdict = 'EMPTY (header only)' if size <= 44 else 'audio present'
            report(f'  user {user_id}: {os.path.basename(path)}, {size} bytes - {verdict}')


async def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        report('ERROR: environment variable DISCORD_TOKEN is empty.')
        sys.exit(2)

    try:
        channel_id = int(sys.argv[1])
    except ValueError:
        report(f'ERROR: "{sys.argv[1]}" is not a channel id.')
        sys.exit(2)

    bot = ProbeBot(channel_id)
    # The task reference has to be kept, otherwise the garbage collector may
    # reclaim it mid-run (a well-known asyncio pitfall).
    task = asyncio.create_task(bot.start(token))
    try:
        await bot.finished.wait()
    finally:
        await bot.close()
        task.cancel()


if __name__ == '__main__':
    asyncio.run(main())
