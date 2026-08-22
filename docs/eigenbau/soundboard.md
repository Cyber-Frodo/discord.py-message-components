# Soundboard

Discords Soundboard — kurze Klänge, die Mitglieder in einem Sprachkanal
abspielen können. Der Upstream kennt es nicht; hier gibt es eine
vollständige Umsetzung.

**Stand: gebaut, aber in keinem Bot benutzt.** Die Beispiele unten sind
deshalb aus dem Code abgeleitet und **nicht gegen Discord gemessen**.

| Datei | Umfang |
| --- | --- |
| `discord/soundboard.py` | **213 Zeilen, komplett neu** |
| `discord/guild.py` | 6 Methoden (+246 Zeilen, inkl. Docstrings) |
| `discord/http.py` | 6 Routen |

## `SoundboardSound`

Erbt von `Hashable`, ist also vergleichbar und als Dict-Schlüssel nutzbar.

| Attribut | Typ | |
| --- | --- | --- |
| `name` | `str` | Anzeigename |
| `sound_id` | `int` | Discords Kennung |
| `volume` | `float` | 0.0 – 1.0 |
| `emoji_id` | `int` | bei eigenem Emoji |
| `emoji_name` | `str` | bei Unicode-Emoji |
| `guild_id` | `int` | Server |
| `available` | `bool` | ob nutzbar (kann bei Boost-Verlust kippen) |
| `user` | `User` | wer ihn angelegt hat |
| `created_at` | `datetime` | aus der Snowflake abgeleitet |

## Die sechs Guild-Methoden

```python
await guild.create_soundboard_sound(name, sound, volume=1.0,
                                    emoji_id=None, emoji_name=None,
                                    auto_trim=False)
await guild.update_soundboard_sound(...)
await guild.delete_soundboard_sound(sound_id)
await guild.get_soundboard_sound(sound_id)
await guild.all_soundboard_sound()        # alle des Servers
await guild.default_soundboard_sounds()   # Discords mitgelieferte
```

`sound` nimmt vier Formen an: **Pfad** (`str` oder `Path`), **rohe Bytes**,
ein **offenes Dateiobjekt** oder eine **Base64-Zeichenkette** — auch als
`data:`-URI.

## `auto_trim` — der eigentliche Wert der Umsetzung

Discord begrenzt Soundboard-Klänge auf **5 Sekunden** und **512 KB**. Wer
darüber liegt, bekommt einen API-Fehler, der nicht sagt, welche der beiden
Grenzen gerissen wurde.

`auto_trim=True` kürzt vorher selbst:

```python
_auto_trim(input_path, max_duration_sec=5, max_size_bytes=512 * 1024)
```

- länger als 5 s → wird geschnitten
- größer als 512 KB → Bitrate wird reduziert, bis es passt

> [!warning] `auto_trim` steht auf `False`, und das ist Absicht
> Automatisches Kürzen verändert die Datei, ohne zu fragen. Wer eine
> 7-Sekunden-Datei hochlädt und nichts angibt, soll den Fehler von Discord
> sehen und nicht stillschweigend einen abgeschnittenen Klang bekommen.

> [!danger] `pydub` ist eine harte Abhängigkeit — und sie steckt an einer unerwarteten Stelle
> `soundboard.py` importiert `pydub` **auf Modulebene**, und `guild.py`
> importiert `soundboard`. Damit hängt **`import discord`** an `pydub`,
> obwohl es mit Soundboard nichts zu tun hat.
>
> Am 22.08.2026 aufgelaufen: Ein Prüfskript für die Sprachverschlüsselung
> scheiterte mit `ModuleNotFoundError: No module named 'pydub'` — an einer
> Stelle, die mit Sound nichts zu tun hatte.
>
> **Dazu kommt:** `pydub` ruft im Hintergrund **ffmpeg** auf. Ohne ffmpeg im
> `PATH` scheitert `auto_trim` zur Laufzeit, nicht beim Import.
>
> **Sauberer wäre**, den Import in `_auto_trim` hineinzuziehen — dann
> braucht ihn nur, wer ihn benutzt. Das ist eine Änderung von zwei Zeilen
> und steht als Vorschlag hier, nicht als erledigt.

## Beispiel

```python
# Aus einer Datei, mit Emoji, ohne automatisches Kürzen
klang = await guild.create_soundboard_sound(
    name='Tusch',
    sound='klaenge/tusch.mp3',
    volume=0.6,
    emoji_name='🎺',
)
print(klang.sound_id, klang.available)

# Mit Kürzen, falls die Quelle zu lang ist
klang = await guild.create_soundboard_sound(
    name='Intro', sound=Path('lang.wav'), auto_trim=True)
```

## Was vor dem ersten produktiven Einsatz zu prüfen ist

1. **Läuft `create_soundboard_sound` überhaupt durch?** Nichts davon ist je
   gegen Discord gelaufen.
2. **Braucht der Server Boost?** Discord staffelt die Anzahl möglicher
   Klänge nach Boost-Stufe — bei Überschreitung kommt ein API-Fehler.
3. **Ist ffmpeg auf dem Zielsystem?** Nur nötig für `auto_trim=True`.
