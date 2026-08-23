# Voice with DAVE

Voice connections after Discord's two encryption changes. Implemented
2026-08-22 on branch `dave-support`.

## Why this is needed

Discord changed the voice layer twice, and this library was left behind both
times:

| Date | What | Consequence here |
| --- | --- | --- |
| **2024-11-18** | The three `xsalsa20_poly1305` modes were removed | They were the **only** ones this fork had. Transport negotiation failed outright. |
| **2026-03-02** | DAVE (end-to-end encryption over MLS) became mandatory for all non-stage channels | The voice gateway rejects with **close code 4017** before a single packet flows |

**This is why `recv_audio()` used to work and then stopped, without anything
changing in this library.** Anyone who remembers getting raw bytes out of it
remembers correctly — that was before 2024-11-18.

## Installation

```bash
py -m pip install "davey>=0.1.6" "PyNaCl>=1.5.0,<1.6"
# or via the extra:
py -m pip install "git+https://github.com/Cyber-Frodo/discord.py-message-components@dave-support#egg=discord.py-message-components[voice]"
```

| Package | Why this exact bound |
| --- | --- |
| `PyNaCl>=1.5.0` | `nacl.secret.Aead` (XChaCha20-Poly1305) only exists from 1.5.0 onward. The mandatory transport mode cannot be built with older versions. |
| `davey>=0.1.6` | Discord's DAVE protocol. Ships wheels for `aarch64` and `armv7l` — a Raspberry Pi needs **no** compiler. |

If `davey` is missing, the connection attempt fails with a message naming the
install command rather than a bare `ImportError`.

## How the two layers interact

This is where a hand-rolled implementation typically fails: **there are two
encryption layers stacked on top of each other.**

```
Sending:    Opus → [DAVE: encrypt_opus] → [transport: aead_…_rtpsize] → UDP
Receiving:  UDP  → [transport: decrypt]  → [DAVE: decrypt]            → Opus
```

Swap the order and you get data that decrypts cleanly and still sounds like
noise.

### Transport: `aead_xchacha20_poly1305_rtpsize`

Packet layout:

```
[ RTP header 12 B ][ CSRC list 4·n ][ ext preamble 4 B ][ ciphertext ][ nonce 4 B ]
└──────────────── authenticated (AAD) ────────────────┘
```

Three things that are easy to get wrong:

1. **The extension header preamble belongs to the AAD**, not to the
   ciphertext. With `_rtpsize` modes it moves into the header — unlike the
   older schemes.
2. **The extension *data* sits inside the ciphertext**, ahead of the audio,
   and must be skipped after decryption.
3. **The CSRC list** (when `cc > 0`) belongs to the header as well.

All of this happens in `RawData` (`sink.py`), not in the cipher methods —
that is where the header flags are known.

> **The nonce belongs to the packet, not to the client.**
> `recv_audio()` runs on its own thread and processes packets from
> **multiple speakers**. A nonce field on the object would be a race
> condition surfacing as intermittent noise — effectively impossible to
> track down.
>
> The first draft had exactly that bug. It was caught by the test case
> "six packets in shuffled order".

### DAVE: the MLS group

`davey` owns the group; the library only routes messages:

| Opcode | What | Handler |
| --- | --- | --- |
| 21 `DAVE_PREPARE_TRANSITION` | transition announced | `_execute_transition()` or `send_transition_ready()` |
| 22 `DAVE_EXECUTE_TRANSITION` | transition takes effect | `_execute_transition()` |
| 24 `DAVE_PREPARE_EPOCH` | new epoch | `reinit_dave_session()` + key package |
| 25 `MLS_EXTERNAL_SENDER` | external sender | `set_external_sender()` |
| 27 `MLS_PROPOSALS` | proposals | `process_proposals()` → commit/welcome back |
| 29 `MLS_ANNOUNCE_COMMIT_TRANSITION` | commit | `process_commit()` |
| 30 `MLS_WELCOME` | admission to the group | `process_welcome()` |
| 31 `MLS_INVALID_COMMIT_WELCOME` | *outbound*: request a rebuild | after a rejected commit |

> **Opcodes 25–31 arrive as *binary* websocket frames.**
> Frame layout: `[ sequence 2 B ][ opcode 1 B ][ payload ]`.
>
> Previously `poll_event()` handled **TEXT only**. Binary frames were
> dropped silently — half the MLS negotiation would have been lost without a
> single error message.

> **Voice gateway v8 is mandatory.**
> The DAVE opcodes only exist from v8 onward. On v4 (the previous state) the
> negotiation would never arrive. v8 also brings replay of missed messages on
> resume, which is why `seq_ack` is tracked.

> **A transition to version 0 means "no DAVE".**
> Passthrough mode must then be enabled (`set_passthrough_mode(True, 120)`),
> otherwise the decryptor keeps trying to decrypt and discards every packet.
> The connection stays up and is **silent anyway** — a failure mode with no
> error message.

## Usage

Unchanged from the old API — it simply works again:

```python
vc = await channel.connect()
vc.start_recording(discord.Sink(encoding='wav', output_path='.'), callback)
await asyncio.sleep(15)
vc.stop_recording()

async def callback(sink, *args):
    for user_id, audio in sink.audio_data.items():
        print(user_id, audio.file)
```

Inspecting state:

```python
vc.mode                      # 'aead_xchacha20_poly1305_rtpsize'
vc.dave_protocol_version     # >0 = DAVE active, 0 = stage channel
vc.dave_session.ready        # ready to encrypt/decrypt
vc.dave_session.voice_privacy_code
```

## Three corrections from 2026-08-23

These came out of debugging a **separate, hand-rolled voice client**
against live Discord. All three were present here too; none of them shows
up in a desk test, and each one is silent - no exception, no log line,
just no sound.

### 1. Binary frames are sent without a sequence prefix

The MLS handshake could never complete. Every binary frame went out as:

```python
struct.pack('>HB', 0, op) + data      #  00 00 <op> <payload>
```

**The frame layout is asymmetric.** Measured against `@discordjs/voice`
(`VoiceWebSocket.ts` lines 129-131 versus line 190):

| Direction | Layout |
| --- | --- |
| receiving | `[ sequence 2 B ][ opcode 1 B ][ payload ]` |
| **sending** | `[ opcode 1 B ][ payload ]` - no sequence |

Discord reads byte 0 as the opcode. With a constant `0` that is
**IDENTIFY**, for *every* frame - the gateway answers close code **4005**
("already authenticated") and tears the connection down mid-handshake.
The key package never arrives.

### 2. Silence frames stay unencrypted

`@discordjs/voice` skips them explicitly on both sides (`DAVESession.ts`
lines 350 and 363 -- verified against the file, not quoted from memory). Sending an *encrypted* silence frame where the
receiver expects plaintext puts it out of step.

The symptom is deceptive: a continuous test tone contains no silence
frames at all and is perfectly audible, while real speech - which is
mostly pauses - stays silent.

### 3. Silence is recognised by length, not by byte pattern

`SILENCE_FRAME` (`f8 ff fe`) is what *this library* emits. Frames from
foreign encoders carry a different TOC byte:

| Byte | |
| --- | --- |
| `f8` = `1111 1000` | config 31, **mono** |
| `fc` = `1111 1100` | config 31, **stereo** |

A browser encoding through WebCodecs sends `fc ff fe`. An exact match on
`f8 ff fe` misses it silently. `is_silence()` therefore decides by
length: no Opus frame of three bytes or fewer carries sound.

> **Why this matters for `recv_audio()`**
> Points 2 and 3 both affect the receive path. A silence frame that is
> handed to `decrypt()` raises
> `DecryptionFailed(UnencryptedWhenPassthroughDisabled)` - the error names
> the cause precisely, but only if someone is reading debug logs. The
> receive loop drops the packet and carries on, so the failure is
> invisible.

## What is measured — and what is not

> **Measured: the encryption, 4 of 4.**
> `test_encryption.py` runs **against the production code**, not against a
> reimplementation:
>
> | Case | |
> | --- | --- |
> | plain packet | 123 B in, 123 B out |
> | with header extension | `ext_offset=8`, 203 B in, 203 B out |
> | with CSRC list | `cc=2`, 20 B header |
> | six packets, shuffled order | all correct |

> **NOT measured on this branch: the connection against live Discord.**
> Whether the MLS negotiation completes cannot be shown by a desk test.
>
> ⚠ **This is not a formality.** The branch shipped with the 4005 bug
> above from 2026-08-22 to 2026-08-23, and it would have surfaced in the
> first second of a live run. "Built" is not "proven".
>
> The three corrections *are* proven, but in the other client - there the
> handshake went from `pending` to `active` immediately, followed by 2 863
> decrypted Opus frames from two speakers and 400 of 400 frames sent
> end-to-end encrypted. Porting them here is a well-founded transfer, not
> a measurement.
>
> `test_voice_receive.py` is included for the real thing:
>
> ```bash
> export DISCORD_TOKEN='...'
> py test_voice_receive.py <voice-channel-id>
> ```
>
> **The proof is a WAV file larger than 44 bytes** — 44 bytes is an empty
> WAV header. A clean log proves nothing: `decrypt()` can succeed and still
> yield noise if the header was split incorrectly.

## What this means for existing bots

**Nothing, as long as nobody calls `channel.connect()`.** The ELYX bot routes
its music through **Lavalink** — verified 2026-08-22: zero calls to
`channel.connect()` across the entire bot, and no code path that inspects the
gateway version. This patch adds capability; it changes no behaviour.
