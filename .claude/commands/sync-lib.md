---
description: Misst den Fork gegen Upstream und gegen die installierten Fassungen, pflegt docs/extras und zieht den Vault nach
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(py:*), Bash(git:*), Bash(gh:*), Bash(ssh:*), Bash(grep:*), Bash(find:*), Bash(wc:*)
---

# /sync-lib — Fork-Doku auf den Stand des Codes bringen

Für [[Discord-Lib - Projekt|Discord-Lib]] — den eigenen Fork von
`mccoderpy/discord.py-message-components`.

> [!important] Dieses Projekt hat **drei** Stände, und sie driften
> | Ort | Was es ist |
> | --- | --- |
> | `…/discord.py-message-components` | **Git-Klon** — Arbeitsort, Quelle des Vault-Imports |
> | `…/discord.py-message-compo.ALT-2026-08-22` | Lesekopie ohne Git, am 22.08.2026 als Altbestand markiert |
>
> ⚠ **Ein fehlendes „nents" entscheidet, ob eine Änderung ankommt.**
> Am 22.08.2026 wurde deshalb ein zweiter Klon angelegt, obwohl der
> richtige danebenlag. **Vor dem Klonen `ls` laufen lassen.**
> | `site-packages` auf PC **und** Pi | **was wirklich läuft** |
>
> Am 22.08.2026 gemessen: Auf dem Pi lag der Fork, auf dem Haupt-PC die
> **Ursprungsfassung** — weil die alte README den Installationsbefehl von
> `mccoderpy` nannte. Schritt 2 prüft genau das.

---

## 1. Abstand zum Upstream messen

```bash
git fetch upstream 2>/dev/null || git remote add upstream https://github.com/mccoderpy/discord.py-message-components.git && git fetch upstream
BASIS=$(git merge-base HEAD upstream/developer)
git log --oneline $BASIS..HEAD | wc -l      # eigene Commits
git diff $BASIS..HEAD --stat | tail -1      # Umfang
```

**Weicht die Zahl von der in `docs/extras/README.md` ab, dort nachziehen** —
mit Datum. Zeilenzahlen veralten schneller als alles andere.

⚠ **Hat der Upstream sich bewegt?** `git log $BASIS..upstream/developer` —
wenn ja, entscheiden: übernehmen oder bewusst stehenlassen. Beides ist
richtig, nur unbemerkt darf es nicht bleiben.

---

## 2. Welche Fassung läuft wo — immer prüfen

```bash
# Haupt-PC
py -c "import discord; print(discord.__version__, hasattr(discord,'ContainerV2'), discord.__file__)"

# Pi (beide Bots teilen sich das globale Python 3.11)
ssh pi 'python3 -c "import discord; print(discord.__version__, hasattr(discord,\"ContainerV2\"))"'
```

**Erwartung: `ContainerV2 = True` überall.** Ist es irgendwo `False`, liegt
dort die Ursprungsfassung — dann ist der CoC-Bot auf diesem Rechner **nicht
lauffähig** (er benutzt `ContainerV2` und `Seperator`), und der Fehler käme
erst zur Laufzeit.

Richtigstellen:

```bash
py -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"
```

⚠ `pydub` fehlt gern — `import discord` hängt daran, weil `soundboard.py`
es auf Modulebene importiert.

---

## 3. Was ist neu am Fork?

```bash
git diff $BASIS..HEAD --stat | grep -v docs/
```

Für jede geänderte Datei prüfen, ob die passende Seite in `docs/extras/`
noch stimmt:

| Datei | Seite |
| --- | --- |
| `components.py`, `types/message.py` | `components-v2.md` |
| `soundboard.py`, `guild.py`, `http.py` | `soundboard.md` |
| `voice_client.py`, `gateway.py`, `sink.py` | `voice-dave.md` |
| `flags.py`, `enums.py`, `client.py` | `flags-and-enums.md` |

**Neue öffentliche Namen finden:**

```bash
git diff $BASIS..HEAD -- discord/ | grep "^+class \|^+    def \|^+    async def "
```

---

## 4. Prüfen

```bash
py -m py_compile $(git ls-files 'discord/*.py')
py test_encryption.py          # 4 von 4 erwartet
```

⚠ **`test_voice_receive.py` braucht einen echten Sprachkanal** und läuft
nicht nebenbei. Solange er nicht gelaufen ist, gilt DAVE als **gebaut, nicht
belegt** — und genau so gehört es in der Doku zu stehen.

**Doku-Bau prüfen**, wenn an `docs/` etwas geändert wurde:

```bash
py -m venv /tmp/sphinxenv && /tmp/sphinxenv/bin/pip install -qr docs/requirements.txt
cd docs && /tmp/sphinxenv/bin/python -m sphinx -b html . /tmp/docbuild
```

⚠ **Aus `docs/` heraus bauen, nicht aus dem Wurzelordner.** Sonst scheitert
es an `_static/scorer.js` — der Pfad wird relativ zum Arbeitsverzeichnis
aufgelöst, und der Fehler sieht aus wie eine fehlende Datei, die es gibt.

**Erwartung: `build succeeded, 30 warnings`.** Die 30 stammen aus
Bibliotheks-Docstrings. Kommen mehr dazu, gehören sie zur eigenen Änderung.

---

## 5. Ausliefern

```bash
git push origin developer-new-features
git log --oneline origin/developer-new-features -1      # GEGENPRÜFEN
```

⚠ **Die Gegenprüfung ist nicht optional.** Am 22.08.2026 sind drei Commits
auf dem falschen Branch gelandet, weil `git push -q` die Meldung
`Everything up-to-date` verschluckt hat. **Nie mit `-q` pushen.**

Read the Docs baut danach von selbst (Webhook). Nach rund einer Minute:

```bash
curl -s https://discord4py-fork.readthedocs.io/en/latest/ | grep -c "Cyber-Frodo"
```

Über 0 heißt: neuer Stand ist live.

---

## 6. Vault nachziehen

```bash
py ~/OneDrive/Desktop/Obsidian-Claude/zweites-gehirn/_werkzeuge/doku-import.py
```

Der Import holt `CLAUDE.md` und die fünf Seiten aus `docs/extras/`.
**`README.rst` bewusst nicht** — RST wäre in Obsidian Rohtext.

Eigene Gedanken gehören in `Discord-Lib - Projekt.md` im Vault; die schreibt
der Import nie.

**Betrifft die Änderung einen Bot?**

| Geändert an | dann prüfen |
| --- | --- |
| `components.py` | **CoC-Bot** — nutzt V2 in vier Dateien |
| `voice_client.py`, `gateway.py` | **ELYX** — fährt Voice über Lavalink, sollte unberührt bleiben |
| irgendetwas Installiertes | beide Bots teilen sich auf dem Pi **ein** Python |

---

## 7. Bericht

- Eigene Commits und Umfang gegenüber Upstream (gemessen, nicht geschätzt)
- Welche Fassung liegt auf PC und Pi
- `test_encryption.py`: wie viele bestanden
- Doku-Bau: Warnungszahl, Abweichung von 30
- Was in `docs/extras/` nachgezogen wurde
- Was **gebaut, aber nicht belegt** ist — namentlich
