# Voice mit DAVE

Sprachverbindungen nach Discords zwei Verschlüsselungsumstellungen.
Gebaut am 22.08.2026 im Branch `dave-support`.

## Warum es das braucht

Discord hat die Voice-Schicht zweimal umgestellt, und diese Bibliothek ist
beide Male stehengeblieben:

| Datum | Was | Folge hier |
| --- | --- | --- |
| **18.11.2024** | Die drei `xsalsa20_poly1305`-Modi abgeschaltet | Sie waren die **einzigen** im Fork. Schon die Aushandlung des Transportverfahrens scheiterte. |
| **02.03.2026** | DAVE (Ende-zu-Ende-Verschlüsselung über MLS) für alle Nicht-Stage-Kanäle Pflicht | Voice-Gateway lehnt mit **Close-Code 4017** ab, bevor ein Paket fließt |

**Deshalb funktionierte `recv_audio()` früher und irgendwann nicht mehr,
ohne dass sich an dieser Bibliothek etwas geändert hätte.** Wer sich erinnert,
damit einmal rohe Bytes bekommen zu haben, erinnert sich richtig — es war vor
dem 18.11.2024.

## Installation

```bash
py -m pip install "davey>=0.1.6" "PyNaCl>=1.5.0,<1.6"
# oder über das Extra:
py -m pip install "git+https://github.com/Cyber-Frodo/discord.py-message-components@dave-support#egg=discord.py-message-components[voice]"
```

| Paket | Warum genau diese Grenze |
| --- | --- |
| `PyNaCl>=1.5.0` | `nacl.secret.Aead` (XChaCha20-Poly1305) gibt es erst ab 1.5.0. Mit älteren Fassungen lässt sich der Pflichtmodus gar nicht bauen. |
| `davey>=0.1.6` | Discords DAVE-Protokoll. Wheels für `aarch64` und `armv7l` — der Raspberry Pi braucht **keinen** Compiler. |

Fehlt `davey`, scheitert erst der Verbindungsversuch — mit einer Meldung,
die den Installationsbefehl nennt statt eines nackten `ImportError`.

## Wie die beiden Schichten zusammenspielen

Das ist der Punkt, an dem eine eigene Umsetzung typischerweise scheitert:
**es sind zwei Verschlüsselungen übereinander.**

```
Senden:     Opus → [DAVE: encrypt_opus] → [Transport: aead_…_rtpsize] → UDP
Empfangen:  UDP  → [Transport: entschlüsseln] → [DAVE: decrypt] → Opus
```

Wer die Reihenfolge vertauscht, bekommt Daten, die sich sauber
entschlüsseln lassen und trotzdem Rauschen ergeben.

### Transport: `aead_xchacha20_poly1305_rtpsize`

Paketaufbau:

```
[ RTP-Header 12 B ][ CSRC-Liste 4·n ][ Ext-Präambel 4 B ][ Geheimtext ][ Nonce 4 B ]
└───────────────── authentifiziert (AAD) ─────────────────┘
```

Drei Dinge, die man falsch machen kann:

1. **Die Präambel der Header-Erweiterung gehört zur AAD**, nicht zum
   Geheimtext. Bei `_rtpsize`-Modi wandert sie in den Header — anders als
   bei den alten Verfahren.
2. **Die Erweiterungs-*Daten* liegen im Geheimtext**, vor dem Audio, und
   müssen nach dem Entschlüsseln übersprungen werden.
3. **Die CSRC-Liste** (falls `cc > 0`) gehört ebenfalls in den Header.

Erledigt wird das in `RawData` (`sink.py`), nicht in den
Verschlüsselungsmethoden — dort sind die Header-Flags bekannt.

> [!danger] Die Nonce gehört ans Paket, nicht an den Client
> `recv_audio()` läuft in einem eigenen Thread und verarbeitet die Pakete
> **mehrerer Sprecher**. Ein Nonce-Feld am Objekt wäre eine Race Condition,
> die sich als sporadisches Rauschen zeigt — praktisch nicht zu finden.
>
> Der erste Entwurf hatte genau diesen Fehler. Gefunden hat ihn der Testfall
> „sechs Pakete in verdrehter Reihenfolge".

### DAVE: die MLS-Gruppe

`davey` führt die Gruppe, die Bibliothek reicht nur durch:

| Opcode | Was | Wohin |
| --- | --- | --- |
| 21 `DAVE_PREPARE_TRANSITION` | Übergang angekündigt | `_execute_transition()` bzw. `send_transition_ready()` |
| 22 `DAVE_EXECUTE_TRANSITION` | Übergang gilt | `_execute_transition()` |
| 24 `DAVE_PREPARE_EPOCH` | neue Epoche | `reinit_dave_session()` + Schlüsselpaket |
| 25 `MLS_EXTERNAL_SENDER` | externer Absender | `set_external_sender()` |
| 27 `MLS_PROPOSALS` | Vorschläge | `process_proposals()` → ggf. Commit/Welcome zurück |
| 29 `MLS_ANNOUNCE_COMMIT_TRANSITION` | Commit | `process_commit()` |
| 30 `MLS_WELCOME` | Aufnahme in die Gruppe | `process_welcome()` |
| 31 `MLS_INVALID_COMMIT_WELCOME` | *ausgehend*: Neuaufbau anfordern | nach abgelehntem Commit |

> [!warning] Die Opcodes 25–31 kommen als **binäre** WebSocket-Rahmen
> Rahmen: `[ Sequenz 2 B ][ Opcode 1 B ][ Nutzlast ]`.
>
> Vorher verarbeitete `poll_event()` **nur TEXT**. Binäre Rahmen fielen
> stillschweigend heraus — damit wäre die halbe MLS-Verhandlung verloren
> gegangen, ohne eine einzige Fehlermeldung.

> [!warning] Voice-Gateway **v8** ist Pflicht
> Die DAVE-Opcodes gibt es erst ab v8. Unter v4 (dem alten Stand) käme die
> Verhandlung nie an. v8 bringt außerdem die Nachlieferung verpasster
> Nachrichten beim Resume — dafür wird `seq_ack` mitgeführt.

> [!note] Übergang auf Version 0 heißt „ohne DAVE"
> Dann muss der Durchreichmodus an (`set_passthrough_mode(True, 120)`),
> sonst versucht der Entschlüssler weiter zu entschlüsseln und verwirft
> jedes Paket. Die Verbindung bleibt bestehen und ist **trotzdem stumm** —
> ein Fehlerbild ohne Fehlermeldung.

## Benutzung

Unverändert zur alten API — es funktioniert jetzt nur wieder:

```python
vc = await kanal.connect()
vc.start_recording(discord.Sink(encoding='wav', output_path='.'), rueckruf)
await asyncio.sleep(15)
vc.stop_recording()

async def rueckruf(sink, *args):
    for nutzer_id, audio in sink.audio_data.items():
        print(nutzer_id, audio.file)
```

Zustand prüfen:

```python
vc.mode                      # 'aead_xchacha20_poly1305_rtpsize'
vc.dave_protocol_version     # >0 = DAVE aktiv, 0 = Stage-Kanal
vc.dave_session.ready        # bereit zum Ver-/Entschlüsseln
vc.dave_session.voice_privacy_code
```

## Was gemessen ist — und was nicht

> [!success] Gemessen: die Verschlüsselung, 4 von 4
> `pruefe_krypto.py` läuft **gegen den Produktivcode**, nicht gegen eine
> Nachbildung:
>
> | Fall | |
> | --- | --- |
> | einfaches Paket | 123 B rein, 123 B raus |
> | mit Header-Erweiterung | `ext_offset=8`, 203 B rein, 203 B raus |
> | mit CSRC-Liste | `cc=2`, Kopf 20 B |
> | sechs Pakete, verdrehte Reihenfolge | alle korrekt |

> [!danger] **Nicht** gemessen: die Verbindung gegen echtes Discord
> Ob die MLS-Verhandlung durchläuft, zeigt kein Schreibtischtest. Dafür
> liegt `pruefe_voice_empfang.py` bei:
>
> ```bash
> export DISCORD_TOKEN='...'
> py pruefe_voice_empfang.py <sprachkanal-id>
> ```
>
> **Der Beleg ist eine WAV-Datei über 44 Byte** — 44 Byte sind ein leerer
> WAV-Kopf. Ein fehlerfreies Log beweist nichts: `decrypt()` kann sauber
> durchlaufen und trotzdem Rauschen liefern, wenn der Header falsch
> abgeteilt wurde.

## Was das für vorhandene Bots bedeutet

**Nichts, solange niemand `channel.connect()` aufruft.** Der ELYX-Bot fährt
seine Musik über **Lavalink** — geprüft am 22.08.2026: 0 Aufrufe von
`channel.connect()` im gesamten Bot, und keine Stelle, die die
Gateway-Version prüft. Der Patch fügt Fähigkeiten hinzu, er ändert kein
Verhalten.
