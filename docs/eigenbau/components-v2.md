# Components V2

Discords zweite Komponentengeneration: Eine Nachricht besteht **vollständig**
aus Komponenten — kein `content`, keine Embeds. Der Fork bringt dafür zehn
Klassen mit, die es im Upstream nicht gibt (`components.py`, +544 Zeilen).

**Im Einsatz:** CoC-Bot (`coc_rework`) — `Clash_King_API.py`, `ignore_ui.py`,
`Tickets.py`, `ignore_news.py`.

## Die Klassen

Alle erben von `BaseComponentV2` und liegen direkt unter `discord.`:

| Klasse | Zweck |
| --- | --- |
| `ContainerV2` | Klammer um alles; nimmt `components=[...]` und `accent_color` |
| `Section` | Textblock **mit** Zubehör rechts (Thumbnail oder Button) |
| `TextDisplay` | Reiner Text, Markdown erlaubt |
| `Thumbnail` | Kleines Bild, nur als Zubehör einer `Section` |
| `MediaGallery` | Bildergalerie, Einträge als `MediaGalleryItemStructure` |
| `FileV2` | Dateianhang als Komponente |
| `Seperator` | Trennlinie — **Schreibweise beachten, siehe unten** |
| `Modal` | Eingabefenster |
| `UnfurledMediaItemStructur` | Medienverweis (`url=`) |
| `MediaGalleryItemStructure` | Einzelner Galerieeintrag |

Gemeinsam: `id`, `type`, `to_dict()`, `from_dict()`.

## Senden — das Flag setzt sich selbst

```python
await ctx.respond(components=[container])
```

Mehr ist nicht nötig. Der Grund steht in `message.py:1522`:

```python
if components and all(isinstance(c, BaseComponentV2) for c in components):
    ...
    flags.is_component_v2 = True
```

> [!warning] Nur wenn **alle** Komponenten V2 sind
> Die Bedingung ist `all(...)`. Eine einzige `ActionRow` in der Liste, und
> das Flag bleibt aus — die Nachricht geht dann als V1 raus, und die
> V2-Komponenten fehlen kommentarlos. **V1 und V2 nicht mischen.**

## Vier Fallen, alle im Betrieb aufgelaufen

> [!danger] 1. `Seperator` ist falsch geschrieben
> Ein „a" fehlt. `discord.Separator` (richtig geschrieben) gibt es **nicht**
> und liefert `AttributeError`.
>
> ```python
> discord.Seperator()    # richtig für diesen Fork
> discord.Separator()    # AttributeError
> ```
>
> Der Tippfehler stammt aus dem Eigenbau und bleibt bewusst stehen: Ihn zu
> korrigieren würde jeden bestehenden Aufruf brechen. Wer ihn eines Tages
> geradezieht, muss `Seperator` als Alias erhalten.

> [!danger] 2. V2 schließt `content` und Embeds aus
> Das Flag schaltet beides ab. Wer zusätzlich ein Embed mitschickt, bekommt
> es nicht angezeigt — ohne Fehlermeldung. **Alles muss Komponente sein.**

> [!danger] 3. `Section` verlangt zwingend ein Zubehör
> `accessory` ist **kein** optionaler Parameter. Wo kein Bild vorliegt,
> nimmt man ein blankes `TextDisplay` statt einer `Section`:
>
> ```python
> if wappen_url:
>     teile.append(discord.Section(
>         components=[discord.TextDisplay(kopf)],
>         accessory=discord.Thumbnail(media=wappen_url)))
> else:
>     teile.append(discord.TextDisplay(kopf))
> ```

> [!warning] 4. Bild-URLs müssen für Discord erreichbar sein
> Discord lädt die Bilder **selbst** nach. Eine Adresse hinter Basic Auth
> oder im LAN liefert dort 401 bzw. gar nichts, und das Bild bleibt leer.
> Im CoC-Bot ist das der Grund, warum Symbole als **Anwendungs-Emoji im
> Text** stehen statt als Bild-URL vom eigenen Dashboard.

## Vollständiges Beispiel aus dem Betrieb

Gekürzt aus `coc_rework/Commandlist/Clash_King_API.py`:

```python
teile = []

# Kopf: mit Wappen als Section, ohne Wappen als reiner Text (Falle 3)
if ident.get('clan_badge'):
    teile.append(discord.Section(
        components=[discord.TextDisplay(kopf)],
        accessory=discord.Thumbnail(media=ident['clan_badge']),
    ))
else:
    teile.append(discord.TextDisplay(kopf))

teile.append(discord.Seperator())
teile.append(discord.TextDisplay('\n'.join([
    '**Kriege**',
    f'Zuverlässigkeit **{krieg["reliability"]} %**',
])))

teile.append(discord.Seperator())
teile.append(discord.TextDisplay('-# Daten aus dem Dashboard'))

return discord.ContainerV2(
    components=teile,
    accent_color=discord.Color.blurple().value,
)
```

`-#` am Zeilenanfang ist Discords Kleinschrift — in `TextDisplay` erlaubt.

## Was noch offen ist

- **Kein Prüfskript.** Ob eine V2-Nachricht wirklich so ankommt, wie sie
  gebaut wurde, zeigt bisher nur der Blick in Discord.
- **`Modal` ist nicht erprobt** — die Klasse steht in `__all__`, taucht aber
  in keinem Bot auf.
- **`FileV2` und `MediaGallery` ebenfalls ungenutzt.** Beide sind gebaut,
  aber nie gegen Discord gelaufen.
