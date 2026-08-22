# Flags, enums and small additions

The small pieces that barely register individually — and are missed the
moment they are needed. All relative to `upstream/developer` (state
2025-04-23).

## `MessageFlags`

Two new values in `flags.py`:

| Flag | Bit | Meaning |
| --- | --- | --- |
| `has_snapshot` | `1 << 14` | The message carries a snapshot — produced by **message forwarding** |
| `is_component_v2` | `1 << 15` | Fully component-driven message |

> **You normally do not set `is_component_v2` yourself.**
> `message.py:1522` sets it automatically as soon as **all** supplied
> components inherit from `BaseComponentV2`. Details in
> [components-v2.md](components-v2.md).

## `ComponentType`

Type IDs for the V2 components:

| Value | Name |
| --- | --- |
| 9 | `Section` |
| 10 | `TextDisplay` |
| 11 | `Thumbnail` |
| 12 | `MediaGallery` |
| 13 | `File` |
| 14 | `Seperator` *(spelled as in the code — see components-v2.md)* |
| 17 | `Container` |

## `MessageType`

Six message kinds Discord added later:

| Value | Name | When |
| --- | --- | --- |
| 36 | `guild_incident_alert_mode_enabled` | security alert enabled |
| 37 | `guild_incident_alert_mode_disabled` | … disabled |
| 38 | `guild_incident_report_raid` | raid reported |
| 39 | `guild_incident_report_false_alarm` | false alarm reported |
| 44 | `purchase_notification` | purchase notification |
| 46 | `poll_result` | poll result |

> **Unknown message types are not a cosmetic problem.**
> When the library meets a type its enum does not know, parsing the message
> can fail. These values are not nice-to-have — they prevent breakage on
> messages nobody anticipated.

## Application emojis

Two client methods plus the route
`GET /applications/{application_id}/emojis`:

```python
await client.all_emojis()                    # emojis owned by the application
await client.fetch_soundboard_sounds(guild_id)
```

**Application emojis belong to the bot application, not to a guild.** They
therefore work on **every** guild the bot is in, without consuming emoji
slots there.

That is exactly what the CoC bot uses them for: icons for town hall, builder
hall and leaderboard appear as application emojis **inside the text** of a
Components V2 message — instead of image URLs pointing at the project's own
dashboard, which sits behind basic auth and would return 401 to Discord.

## Other touched files

Changed along the way, without gaining their own API:

| File | Lines | For |
| --- | --- | --- |
| `types/message.py` | +106 | type hints for the V2 payloads |
| `interactions.py` | +68 | `respond()` accepts `BaseComponentV2` |
| `state.py` | +59 | events for soundboard and V2 |
| `message.py` | +91 | automatic flag, `all_components()` walks V2 |
| `abc.py` · `channel.py` | +12 / +4 | passing components through on send |
