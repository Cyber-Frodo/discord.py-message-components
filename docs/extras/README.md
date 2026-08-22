# Fork extras — what this fork adds

This folder documents **only the additions** made in this fork on top of
`mccoderpy/discord.py-message-components`. Everything else is covered by the
upstream Sphinx documentation one level up.

**Why a separate folder:** upstream docs get overwritten whenever the fork is
synced with its origin. What lives here survives that.

## Divergence point and size

Measured 2026-08-22 with `git merge-base`:

| | |
| --- | --- |
| Forked from | `upstream/developer`, commit `847d53f` (**2025-04-23**) |
| Own commits since | **39** |
| Size | **1,660 lines across 23 files** |

Re-measure when these numbers go stale:

```bash
git remote add upstream https://github.com/mccoderpy/discord.py-message-components.git
git fetch upstream
git diff $(git merge-base HEAD upstream/developer)..HEAD --stat
```

## The four areas

| Area | What | Docs |
| --- | --- | --- |
| **Components V2** | 10 new component classes for fully component-driven messages | [components-v2.md](components-v2.md) |
| **Soundboard** | `SoundboardSound` plus six guild methods and six HTTP routes | [soundboard.md](soundboard.md) |
| **Voice with DAVE** | Voice send and receive after Discord's encryption changes | [voice-dave.md](voice-dave.md) |
| **Flags and enums** | `is_component_v2`, `has_snapshot`, new message types | [flags-and-enums.md](flags-and-enums.md) |

## Where these are actually used

Not hypothetical — two of them run in production bots:

| Addition | Used in |
| --- | --- |
| Components V2 | **CoC bot**: `Clash_King_API.py`, `ignore_ui.py`, `Tickets.py`, `ignore_news.py` |
| Voice / DAVE | nowhere yet — the ELYX bot routes its music through **Lavalink** and never calls `channel.connect()` |
| Soundboard | nowhere yet |

> **The repository is not what Python imports.**
> Installation happens through `pip`, and imports resolve from
> `site-packages`. Editing a cloned checkout changes nothing until it is
> installed:
>
> ```bash
> py -m pip install "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@<branch>"
> ```
>
> On a Raspberry Pi, install into the venv of the bot that needs it — not
> globally. Otherwise two bots end up on different versions and nobody
> notices.

## Known pitfalls

| Issue | Where |
| --- | --- |
| `Seperator` is misspelled (missing an `a`) | [components-v2.md](components-v2.md) |
| `soundboard.py` pulls in **pydub**, a hard dependency the rest of the library does not need | [soundboard.md](soundboard.md) |
| Voice has required `davey` since 2026-03-02 | [voice-dave.md](voice-dave.md) |
