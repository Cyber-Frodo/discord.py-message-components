discord.py-message-components — eigener Fork
============================================

*A personal fork of* `mccoderpy/discord.py-message-components <https://github.com/mccoderpy/discord.py-message-components>`_
*with Components V2, Soundboard and DAVE voice support. Documentation is in German.*

Fork von `mccoderpy/discord.py-message-components <https://github.com/mccoderpy/discord.py-message-components>`_
mit eigenen Erweiterungen. Diese Datei beschreibt **nur**, was hier anders
ist — alles Übrige steht in der `Original-Dokumentation
<https://discordpy-message-components.readthedocs.io/en/developer/>`_.

.. warning::

    **Nicht vom Original installieren.** Der Befehl aus der Original-README

    .. code:: sh

        py -m pip install -U git+https://github.com/mccoderpy/discord.py-message-components.git@developer

    installiert die Ursprungsfassung und **entfernt damit alle Erweiterungen
    dieses Forks** — Components V2, Soundboard, DAVE. Bots, die darauf
    aufbauen, brechen dann mit ``AttributeError``.

    Am 22.08.2026 nachgemessen: Auf dem Haupt-PC lag genau deshalb die
    Ursprungsfassung, ohne ``ContainerV2`` und ohne ``SoundboardSound``.

Installation
------------

.. code:: sh

    # Windows
    py -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"

    # Linux / Raspberry Pi
    python3 -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"

Mit Sprachunterstützung (siehe ``docs/eigenbau/voice-dave.md``):

.. code:: sh

    py -m pip install -U "discord.py-message-components[voice] @ git+https://github.com/Cyber-Frodo/discord.py-message-components.git@dave-support"

Das ``voice``-Extra zieht ``PyNaCl>=1.5.0,<1.6`` und ``davey>=0.1.6``.
Beide sind zwingend: Discord verlangt seit dem **02.03.2026** DAVE-
Verschlüsselung, und ``nacl.secret.Aead`` gibt es erst ab PyNaCl 1.5.0.

.. note::

    Diese Bibliothek überschreibt ``import discord``. Ein zuvor installiertes
    ``discord.py`` vorher entfernen:

    .. code:: sh

        py -m pip uninstall discord.py

Was dieser Fork zusätzlich kann
-------------------------------

Stand 22.08.2026: **39 eigene Commits, 1 660 Zeilen in 23 Dateien**,
abgezweigt von ``upstream/developer`` (``847d53f``, 23.04.2025).

+----------------------+----------------------------------------------------------+------------------------+
| Bereich              | Inhalt                                                   | Doku                   |
+======================+==========================================================+========================+
| **Components V2**    | 10 Klassen: ``ContainerV2``, ``Section``,                | ``docs/eigenbau/``     |
|                      | ``TextDisplay``, ``Thumbnail``, ``MediaGallery``,        | ``components-v2.md``   |
|                      | ``FileV2``, ``Seperator``, ``Modal`` u. a.               |                        |
+----------------------+----------------------------------------------------------+------------------------+
| **Soundboard**       | ``SoundboardSound``, sechs ``Guild``-Methoden,           | ``docs/eigenbau/``     |
|                      | automatisches Kürzen auf 5 s / 512 KB                    | ``soundboard.md``      |
+----------------------+----------------------------------------------------------+------------------------+
| **Voice mit DAVE**   | ``aead_xchacha20_poly1305_rtpsize``, MLS über ``davey``, | ``docs/eigenbau/``     |
|                      | Voice-Gateway v8 — Empfang funktioniert wieder           | ``voice-dave.md``      |
+----------------------+----------------------------------------------------------+------------------------+
| **Flags und Enums**  | ``is_component_v2``, ``has_snapshot``, neue              | ``docs/eigenbau/``     |
|                      | Nachrichtentypen, Anwendungs-Emojis                      | ``flags-und-enums.md`` |
+----------------------+----------------------------------------------------------+------------------------+

Ausführlich: `docs/eigenbau/README.md <docs/eigenbau/README.md>`_

Zwei Fallen vorweg
------------------

.. warning::

    **1. ``Seperator`` ist falsch geschrieben** — ein „a" fehlt.
    ``discord.Separator`` gibt es nicht und liefert ``AttributeError``.
    Der Tippfehler bleibt bewusst stehen: Ihn zu korrigieren würde jeden
    bestehenden Aufruf brechen.

    **2. ``import discord`` braucht pydub.** ``soundboard.py`` importiert es
    auf Modulebene, und ``guild.py`` importiert ``soundboard``. Damit hängt
    der Import der ganzen Bibliothek daran, auch wenn kein Sound im Spiel
    ist. ``pydub`` ruft seinerseits **ffmpeg** auf.

Branches
--------

+------------------------------+------------------------------------------------------+
| ``developer-new-features``   | Hauptzweig dieses Forks — Components V2, Soundboard  |
+------------------------------+------------------------------------------------------+
| ``dave-support``             | zusätzlich Sprachunterstützung mit DAVE              |
+------------------------------+------------------------------------------------------+

Beispiele
---------

Im Ordner `examples <examples>`_ sowie in der `Original-Dokumentation
<https://discordpy-message-components.readthedocs.io/en/developer/>`_.

Für die **eigenen** Erweiterungen stehen vollständige Beispiele in
``docs/eigenbau/`` — darunter ein Components-V2-Aufbau aus dem laufenden
Betrieb.

Herkunft und Lizenz
-------------------

Dieser Fork basiert auf
`mccoderpy/discord.py-message-components <https://github.com/mccoderpy/discord.py-message-components>`_,
das seinerseits auf `discord.py <https://github.com/Rapptz/discord.py>`_ von
Rapptz aufbaut. Lizenz unverändert: **MIT** (siehe ``LICENSE``).

Fehlerberichte zum **Ursprungsprojekt** gehören dorthin, nicht hierher:
`Issues bei mccoderpy <https://github.com/mccoderpy/discord.py-message-components/issues>`_
· `Support-Server <https://discord.gg/sb69muSqsg>`_
