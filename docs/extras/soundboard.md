# Soundboard

Discord's soundboard — short clips members can play in a voice channel.
Upstream has no support for it; this fork implements it fully.

**Status: built, but not used by any bot.** The examples below are derived
from the code and have **never been measured against Discord**.

| File | Size |
| --- | --- |
| `discord/soundboard.py` | **213 lines, entirely new** |
| `discord/guild.py` | 6 methods (+246 lines including docstrings) |
| `discord/http.py` | 6 routes |

## `SoundboardSound`

Inherits from `Hashable`, so it compares by ID and works as a dict key.

| Attribute | Type | |
| --- | --- | --- |
| `name` | `str` | display name |
| `sound_id` | `int` | Discord's ID |
| `volume` | `float` | 0.0 – 1.0 |
| `emoji_id` | `int` | for custom emoji |
| `emoji_name` | `str` | for unicode emoji |
| `guild_id` | `int` | owning guild |
| `available` | `bool` | usable (can flip when boost level drops) |
| `user` | `User` | who created it |
| `created_at` | `datetime` | derived from the snowflake |

## The six guild methods

```python
await guild.create_soundboard_sound(name, sound, volume=1.0,
                                    emoji_id=None, emoji_name=None,
                                    auto_trim=False)
await guild.update_soundboard_sound(...)
await guild.delete_soundboard_sound(sound_id)
await guild.get_soundboard_sound(sound_id)
await guild.all_soundboard_sound()        # all sounds of the guild
await guild.default_soundboard_sounds()   # Discord's built-in ones
```

`sound` accepts four forms: a **path** (`str` or `Path`), **raw bytes**, an
**open file object**, or a **base64 string** — including a `data:` URI.

## `auto_trim` — the actual value of this implementation

Discord limits soundboard clips to **5 seconds** and **512 KB**. Exceeding
either returns an API error that does not say which limit was hit.

`auto_trim=True` shortens the input beforehand:

```python
_auto_trim(input_path, max_duration_sec=5, max_size_bytes=512 * 1024)
```

- longer than 5 s → cut
- larger than 512 KB → bitrate reduced until it fits

> **`auto_trim` defaults to `False`, and that is deliberate.**
> Trimming silently alters the file. Someone uploading a 7-second clip
> without opting in should see Discord's error rather than quietly receive a
> truncated sound.

> **`pydub` is a hard dependency — in an unexpected place.**
> `soundboard.py` imports `pydub` at **module level**, and `guild.py` imports
> `soundboard`. That makes **`import discord`** depend on `pydub`, even
> though it has nothing to do with soundboards.
>
> Hit on 2026-08-22: a test script for voice encryption failed with
> `ModuleNotFoundError: No module named 'pydub'` — in a place entirely
> unrelated to sound.
>
> **On top of that:** `pydub` shells out to **ffmpeg**. Without ffmpeg on
> `PATH`, `auto_trim` fails at runtime, not at import time.
>
> **The clean fix** is to move the import inside `_auto_trim`, so only
> callers that need it pay for it. That is a two-line change and is recorded
> here as a proposal, not as done.

## Example

```python
# From a file, with an emoji, no automatic trimming
sound = await guild.create_soundboard_sound(
    name='Fanfare',
    sound='clips/fanfare.mp3',
    volume=0.6,
    emoji_name='🎺',
)
print(sound.sound_id, sound.available)

# With trimming, in case the source is too long
sound = await guild.create_soundboard_sound(
    name='Intro', sound=Path('long.wav'), auto_trim=True)
```

## To verify before first production use

1. **Does `create_soundboard_sound` even succeed?** None of this has ever
   run against Discord.
2. **Does the guild need boosting?** Discord scales the number of allowed
   sounds by boost level; exceeding it returns an API error.
3. **Is ffmpeg present on the target system?** Only needed for
   `auto_trim=True`.
