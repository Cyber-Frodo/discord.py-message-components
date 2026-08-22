# Flags, Enums und Kleinteile

Die kleinen Ergänzungen, die einzeln kaum auffallen — aber fehlen, sobald
man sie braucht. Alles gegenüber `upstream/developer` (Stand 23.04.2025).

## `MessageFlags`

Zwei neue Werte in `flags.py`:

| Flag | Bit | Bedeutung |
| --- | --- | --- |
| `has_snapshot` | `1 << 14` | Die Nachricht enthält einen Schnappschuss — entsteht beim **Weiterleiten** einer Nachricht |
| `is_component_v2` | `1 << 15` | Vollständig komponentengetriebene Nachricht |

> [!note] `is_component_v2` setzt man normalerweise nicht selbst
> `message.py:1522` setzt es automatisch, sobald **alle** übergebenen
> Komponenten von `BaseComponentV2` erben. Details in
> [components-v2.md](components-v2.md).

## `ComponentType`

Die Typkennungen der V2-Komponenten:

| Wert | Name |
| --- | --- |
| 9 | `Section` |
| 10 | `TextDisplay` |
| 11 | `Thumbnail` |
| 12 | `MediaGallery` |
| 13 | `File` |
| 14 | `Seperator` *(Schreibweise wie im Code — siehe components-v2.md)* |
| 17 | `Container` |

## `MessageType`

Sechs Nachrichtenarten, die Discord nachgereicht hat:

| Wert | Name | Wann |
| --- | --- | --- |
| 36 | `guild_incident_alert_mode_enabled` | Sicherheitswarnung eingeschaltet |
| 37 | `guild_incident_alert_mode_disabled` | … ausgeschaltet |
| 38 | `guild_incident_report_raid` | Raid gemeldet |
| 39 | `guild_incident_report_false_alarm` | Fehlalarm gemeldet |
| 44 | `purchase_notification` | Kaufbenachrichtigung |
| 46 | `poll_result` | Ergebnis einer Umfrage |

> [!warning] Unbekannte Nachrichtentypen sind kein kosmetisches Problem
> Trifft die Bibliothek auf einen Typ, den ihr Enum nicht kennt, kann das
> Auswerten der Nachricht scheitern. Diese Werte sind also nicht „nice to
> have" — sie verhindern Ausfälle bei Nachrichten, die niemand
> vorhergesehen hat.

## Anwendungs-Emojis

Zwei Methoden am `Client`, plus die Route
`GET /applications/{application_id}/emojis`:

```python
await client.all_emojis()                    # Emojis der Anwendung
await client.fetch_soundboard_sounds(guild_id)
```

**Anwendungs-Emojis gehören der Bot-Anwendung, nicht einem Server.** Sie
funktionieren damit auf **jedem** Server, auf dem der Bot ist, ohne dort
Emoji-Plätze zu belegen.

Genau dafür werden sie im CoC-Bot benutzt: Symbole für Rathaus,
Meisterhütte und Rangliste stehen als Anwendungs-Emoji **im Text** einer
Components-V2-Nachricht — statt als Bild-URL vom eigenen Dashboard, das
hinter Basic Auth liegt und Discord nur 401 liefern würde.

## Weitere Berührungspunkte

Diese Dateien wurden mitgeändert, ohne eigene API zu bekommen:

| Datei | Zeilen | Wofür |
| --- | --- | --- |
| `types/message.py` | +106 | Typangaben für die V2-Nutzlasten |
| `interactions.py` | +68 | `respond()` nimmt `BaseComponentV2` |
| `state.py` | +59 | Ereignisse für Soundboard und V2 |
| `message.py` | +91 | automatisches Flag, `all_components()` durchläuft V2 |
| `abc.py` · `channel.py` | +12 / +4 | Weiterreichen der Komponenten beim Senden |
