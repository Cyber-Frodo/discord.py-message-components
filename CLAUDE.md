# discord.py-message-components — Arbeitskontext

Lokale Arbeitskopie des Forks, auf dem **ELYX** läuft. Diese Datei ist der
Einstieg für eine neue Sitzung: was hier liegt, wie es sich zur installierten
Fassung verhält, und die Fallen, die in ELYX schon Zeit gekostet haben.

**Stand:** 16.08.2026 · 95 Python-Dateien · **64 538 Zeilen**

> [!warning] Das hier ist **kein** eigenständiges Projekt, sondern eine Kopie
> Es gibt **kein Git-Repo** in diesem Ordner und keine `setup.py`. Es ist der
> ausgepackte Paketinhalt — derselbe Baum, der sonst unter `site-packages/discord`
> liegt. Wer hier etwas ändert, ändert **nichts** an dem, was Python lädt.
>
> Der Bot importiert die **installierte** Fassung, nicht diese.

---

## Verhältnis zur installierten Fassung — sie sind NICHT gleich

Am 16.08.2026 Datei für Datei per MD5 verglichen:

| | |
| --- | --- |
| installiert (Haupt-PC) | `2.0a737+ga537cbb` |
| Dateien **gleich** | **81** |
| Dateien **abweichend** | **13** |
| nur in dieser Kopie | 1 |

Abweichend sind: `__init__.py`, `application_commands.py`, `client.py`,
`components.py`, `enums.py`, `flags.py`, `gateway.py`, `guild.py`, `http.py`,
`message.py` und drei weitere.

`gateway.py` hat hier **985 Zeilen**, installiert **970**. Welche der beiden
neuer ist, wurde **nicht** geklärt — beide tragen `__version__ = '2.0a'`, und
die Datei nennt keine Commit-Kennung.

> [!danger] Daraus folgt die wichtigste Regel für diesen Ordner
> **Bevor du hier etwas liest und daraus schließt, wie sich der Bot verhält:
> prüfe, ob die Stelle in der installierten Fassung genauso aussieht.**
>
> ```bash
> # Git Bash, aus einem BELIEBIGEN anderen Verzeichnis (siehe types/-Falle)
> py -c "import discord, pathlib; print(pathlib.Path(discord.__file__).parent)"
> diff <path-hier>/gateway.py <installierter-pfad>/gateway.py
> ```
>
> 13 von 95 Dateien weichen ab. Die Wahrscheinlichkeit, ausgerechnet eine
> davon zu erwischen, ist nicht klein — `gateway.py`, `client.py` und
> `http.py` sind genau die, in denen man beim Debuggen nachsieht.

---

## ⚠ In diesem Ordner lässt sich kein Python starten

```
ImportError: cannot import name 'MappingProxyType' from 'types'
```

Der Ordner enthält ein Verzeichnis **`types/`** (17 Dateien, 2 078 Zeilen mit
den TypedDicts der Discord-API). Startet man Python *innerhalb* dieses
Ordners, steht `''` am Anfang von `sys.path` — und `types/` verschattet damit
Pythons **Standardmodul** `types`. Der Fehler kommt aus `enum.py`, also lange
bevor irgendetwas von Discord geladen wird.

**Immer aus einem anderen Verzeichnis arbeiten** und den Pfad übergeben:

```bash
cd ~/Desktop            # irgendwo anders hin
py -c "import pathlib; p = pathlib.Path('Alle Projekte/discord/discord.py-message-compo'); ..."
```

---

## Aufbau

| Teil | Umfang | Inhalt |
| --- | --- | --- |
| Hauptmodule | 68 Dateien | `channel.py` (4 182), `guild.py` (4 018), `client.py` (3 400), `application_commands.py` (2 492), `message.py` (2 155) … |
| `ext/` | 12 Dateien, 9 458 Zeilen | `commands` (Cogs, Checks), `tasks` (Schleifen) |
| `oauth2/` | 8 Dateien, 4 104 Zeilen | OAuth2-Client — von ELYX **nicht** benutzt |
| `types/` | 17 Dateien, 2 078 Zeilen | TypedDicts der API-Nutzlasten (siehe Falle oben) |
| `bin/` | 2 DLLs | `libopus-0.x64.dll` und `-x86.dll` — **nur Windows**. Auf dem Pi kommt libopus aus dem System. |

---

## Die Fallen — alle am 16.08.2026 im Quelltext dieser Kopie verortet

Diese Punkte stehen auch in der ELYX-`CLAUDE.md`; hier stehen die **Fundstellen**.

### `Loop.next_iteration` ist eine Property ohne Setter

`ext/tasks/__init__.py:152` — **0 Treffer** für `next_iteration.setter`.

Eine Zuweisung wirft `AttributeError` *vor* dem `try` in `Loop._loop()`. Der
Task endet, die Schleife tickt nie, und es steht **nichts** im Log. Im
CoC-Projekt sind daran alle vier Schleifen gestorben.

### `Asset` hat kein `.url`

`asset.py:69` definiert die Klasse, ein `def url` gibt es darin **nicht**.
`asset.url` ist discord.py-2.x-Syntax. Richtig ist `str(asset)`.

### Knöpfe über `custom_id`, nicht über `View`

`ext/commands/cog.py:369` (`on_click`) und `:432` (`on_select`). Das ist die
eigentliche Besonderheit dieses Forks gegenüber discord.py — deshalb wird er
überhaupt benutzt.

Die Muster werden mit `re.match` geprüft; ein unverankertes `ticket` fängt
deshalb auch `ticket_loeschen`. Immer `^…$` schreiben.

### `AutoModAction.to_dict()` ist kaputt

`automod.py:171–173`:

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        'type': int(self.type)      # <- self.type ist _EnumValue_… ohne __int__
```

`int()` auf einem `_EnumValue_AutoModActionType` wirft `TypeError`. Die Klasse
kann ihr eigenes Objekt nicht serialisieren — **jeder** Aufruf von
`guild.create_automod_rule()` stirbt. ELYX umgeht das über `bot.http`
(rohes Dict) statt über die Bibliotheksmethode.

⚠ Der **Konstruktor läuft durch**; der Fehler kommt erst beim Serialisieren.
Wer nur „Objekt lässt sich bauen" prüft, hält den Weg für gangbar.

### Kein globaler Check für Slash-Befehle

`bot.add_check()` gilt nur für **Präfix**-Befehle. Ausgewertet wird
`__commands_checks__` **auf der Befehlsfunktion** — siehe
`application_commands.py`, `can_run()`. ELYX hängt darüber die
Dashboard-Schalter an alle Befehle.

### Voice-Gateway v4 — Musik ist damit unmöglich

`gateway.py:836`:

```python
gateway = 'wss://' + client.endpoint + '/?v=4'
```

**Discord erzwingt seit dem 01.03.2026 das DAVE-Protokoll** (Ende-zu-Ende-
Verschlüsselung) für alle Sprachverbindungen außer in **Stage-Kanälen**.
DAVE gibt es ab Voice-Gateway **v8**. Mit `v=4` antwortet Discord mit
Close-Code **4006**; am 16.08.2026 im ELYX-Log fünfmal gemessen.

Ausführlich in [README.md](README.md), Abschnitt „Kann man DAVE nachrüsten?".

---

## Wenn du hier etwas änderst

1. **Es wirkt nicht.** Der Bot lädt die installierte Fassung. Wer eine
   Änderung testen will, muss sie nach `site-packages/discord/` kopieren —
   und weiß dann, dass ein `pip install` sie wieder überschreibt.
2. **Erst diffen, dann schließen.** 13 von 95 Dateien weichen ab.
3. **Nie Python in diesem Ordner starten** — `types/` verschattet das
   Standardmodul.
4. **Diese Datei und `README.md` sind von Hand geschrieben.** Sie gehören
   nicht zum Paket und werden von einem `pip install` gelöscht.
