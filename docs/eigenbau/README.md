# Eigenbau — was dieser Fork zusätzlich kann

Dieser Ordner dokumentiert **nur die eigenen Erweiterungen** gegenüber
`mccoderpy/discord.py-message-components`. Alles andere steht in der
Sphinx-Doku eine Ebene höher (`docs/`, englisch).

**Warum getrennt:** Die Upstream-Doku wird bei jedem Abgleich überschrieben.
Was hier steht, überlebt das — und es ist auf Deutsch, weil es Arbeitsdoku
ist und keine Veröffentlichung.

## Abzweigpunkt und Umfang

Gemessen am 22.08.2026 mit `git merge-base`:

| | |
| --- | --- |
| Abzweig von | `upstream/developer`, Commit `847d53f` vom **23.04.2025** |
| Eigene Commits seither | **39** |
| Umfang | **1 660 Zeilen in 23 Dateien** |

So wird nachgemessen, wenn die Zahl veraltet:

```bash
git remote add upstream https://github.com/mccoderpy/discord.py-message-components.git
git fetch upstream
git diff $(git merge-base HEAD upstream/developer)..HEAD --stat
```

## Die vier Bereiche

| Bereich | Was | Doku |
| --- | --- | --- |
| **Components V2** | 10 neue Komponentenklassen für vollständig komponentengetriebene Nachrichten | [components-v2.md](components-v2.md) |
| **Soundboard** | `SoundboardSound` plus sechs Guild-Methoden und sechs HTTP-Routen | [soundboard.md](soundboard.md) |
| **Voice mit DAVE** | Sprachempfang und -versand nach Discords Verschlüsselungsumstellung | [voice-dave.md](voice-dave.md) |
| **Flags und Enums** | `is_component_v2`, `has_snapshot`, neue Nachrichtentypen | [flags-und-enums.md](flags-und-enums.md) |

## Wo das benutzt wird

Nicht theoretisch — beides läuft in eigenen Bots:

| Erweiterung | Verwendung |
| --- | --- |
| Components V2 | **CoC-Bot** (`coc_rework`): `Clash_King_API.py`, `ignore_ui.py`, `Tickets.py`, `ignore_news.py` |
| Voice / DAVE | noch nirgends — ELYX fährt seine Musik über **Lavalink** und ruft `channel.connect()` nirgends auf |
| Soundboard | noch nirgends |

> [!important] Der Fork ist **nicht** das, was Python lädt
> Installiert wird über `pip`, geladen aus `site-packages`. Eine Änderung im
> geklonten Ordner wirkt **nicht**, bevor sie installiert ist:
>
> ```bash
> py -m pip install "git+https://github.com/Cyber-Frodo/discord.py-message-components@<branch>"
> ```
>
> Auf dem Raspberry Pi in das venv des jeweiligen Bots installieren, nicht
> global — sonst laufen zwei Bots auf unterschiedlichen Ständen, ohne dass
> es jemandem auffällt.

## Bekannte Stolpersteine

| Was | Wo |
| --- | --- |
| `Seperator` ist falsch geschrieben (ein „a" fehlt) | [components-v2.md](components-v2.md) |
| `soundboard.py` zieht **pydub** — eine harte Abhängigkeit, die der Rest der Bibliothek nicht braucht | [soundboard.md](soundboard.md) |
| Voice braucht seit 02.03.2026 zwingend `davey` | [voice-dave.md](voice-dave.md) |
