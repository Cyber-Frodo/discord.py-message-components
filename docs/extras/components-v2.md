# Components V2

Discord's second component generation: a message consists **entirely** of
components — no `content`, no embeds. This fork adds ten classes for it that
upstream does not have (`components.py`, +544 lines).

**In production:** CoC bot — `Clash_King_API.py`, `ignore_ui.py`,
`Tickets.py`, `ignore_news.py`.

## The classes

All inherit from `BaseComponentV2` and live directly under `discord.`:

| Class | Purpose |
| --- | --- |
| `ContainerV2` | Wraps everything; takes `components=[...]` and `accent_color` |
| `Section` | Text block **with** an accessory on the right (thumbnail or button) |
| `TextDisplay` | Plain text, Markdown allowed |
| `Thumbnail` | Small image, only valid as a `Section` accessory |
| `MediaGallery` | Image gallery, entries are `MediaGalleryItemStructure` |
| `FileV2` | File attachment as a component |
| `Seperator` | Divider — **mind the spelling, see below** |
| `Modal` | Input dialog |
| `UnfurledMediaItemStructur` | Media reference (`url=`) |
| `MediaGalleryItemStructure` | Single gallery entry |

Shared API: `id`, `type`, `to_dict()`, `from_dict()`.

## Sending — the flag sets itself

```python
await ctx.respond(components=[container])
```

That is all. The reason is in `message.py:1522`:

```python
if components and all(isinstance(c, BaseComponentV2) for c in components):
    ...
    flags.is_component_v2 = True
```

> **Only when *every* component is V2.**
> The condition is `all(...)`. A single `ActionRow` in the list and the flag
> stays off — the message then goes out as V1 and the V2 components are
> dropped without a word. **Do not mix V1 and V2.**

## Four pitfalls, all hit in production

> **1. `Seperator` is misspelled.**
> One `a` is missing. `discord.Separator` (the correct spelling) does **not**
> exist and raises `AttributeError`.
>
> ```python
> discord.Seperator()    # correct for this fork
> discord.Separator()    # AttributeError
> ```
>
> The typo comes from this fork and stays on purpose: fixing it would break
> every existing call. Whoever corrects it one day must keep `Seperator` as
> an alias.

> **2. V2 excludes `content` and embeds.**
> The flag disables both. Passing an embed alongside means it simply is not
> rendered — with no error. **Everything must be a component.**

> **3. `Section` requires an accessory.**
> `accessory` is **not** optional. Where no image is available, use a bare
> `TextDisplay` instead of a `Section`:
>
> ```python
> if badge_url:
>     parts.append(discord.Section(
>         components=[discord.TextDisplay(header)],
>         accessory=discord.Thumbnail(media=badge_url)))
> else:
>     parts.append(discord.TextDisplay(header))
> ```

> **4. Image URLs must be reachable by Discord.**
> Discord fetches images **itself**. An address behind basic auth or on a
> private network returns 401 or nothing at all, and the image stays blank.
> In the CoC bot this is why icons are **application emojis inside the text**
> rather than image URLs pointing at the project's own dashboard.

## Full example from production

Condensed from `coc_rework/Commandlist/Clash_King_API.py`:

```python
parts = []

# Header: Section when a badge exists, plain text otherwise (pitfall 3)
if ident.get('clan_badge'):
    parts.append(discord.Section(
        components=[discord.TextDisplay(header)],
        accessory=discord.Thumbnail(media=ident['clan_badge']),
    ))
else:
    parts.append(discord.TextDisplay(header))

parts.append(discord.Seperator())
parts.append(discord.TextDisplay('\n'.join([
    '**Wars**',
    f'Reliability **{war["reliability"]} %**',
])))

parts.append(discord.Seperator())
parts.append(discord.TextDisplay('-# Data from the dashboard'))

return discord.ContainerV2(
    components=parts,
    accent_color=discord.Color.blurple().value,
)
```

`-#` at the start of a line is Discord's small text — allowed inside
`TextDisplay`.

## Still open

- **No test script.** Whether a V2 message actually arrives as built is so
  far only verified by looking at Discord.
- **`Modal` is unproven** — the class is exported but appears in no bot.
- **`FileV2` and `MediaGallery` likewise unused.** Both are implemented but
  have never run against Discord.
