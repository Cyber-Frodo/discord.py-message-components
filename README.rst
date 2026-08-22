discord.py-message-components — personal fork
=============================================

Fork of `mccoderpy/discord.py-message-components <https://github.com/mccoderpy/discord.py-message-components>`_
with additional features. This file documents **only** what differs here —
everything else is covered by the `upstream documentation
<https://discordpy-message-components.readthedocs.io/en/developer/>`_.

.. warning::

    **Do not install from upstream.** The command in the upstream README

    .. code:: sh

        py -m pip install -U git+https://github.com/mccoderpy/discord.py-message-components.git@developer

    installs the original version and therefore **removes every addition made
    in this fork** — Components V2, Soundboard, DAVE. Bots relying on those
    break with ``AttributeError``.

    That is not hypothetical. On 2026-08-22 the main workstation had exactly
    that state, verified with ``hasattr(discord, 'ContainerV2') -> False``.

Installation
------------

.. code:: sh

    # Windows
    py -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"

    # Linux / Raspberry Pi
    python3 -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"

With voice support (see ``docs/extras/voice-dave.md``):

.. code:: sh

    py -m pip install -U "discord.py-message-components[voice] @ git+https://github.com/Cyber-Frodo/discord.py-message-components.git@dave-support"

The ``voice`` extra pulls ``PyNaCl>=1.5.0,<1.6`` and ``davey>=0.1.6``. Both
bounds are mandatory: Discord has required DAVE encryption since
**2026-03-02**, and ``nacl.secret.Aead`` only exists from PyNaCl 1.5.0
onward.

.. note::

    This library overrides ``import discord``. Remove a previously installed
    ``discord.py`` first:

    .. code:: sh

        py -m pip uninstall discord.py

What this fork adds
-------------------

As of 2026-08-22: **39 own commits, 1,660 lines across 23 files**, forked
from ``upstream/developer`` (``847d53f``, 2025-04-23).

+----------------------+----------------------------------------------------------+------------------------+
| Area                 | Contents                                                 | Docs                   |
+======================+==========================================================+========================+
| **Components V2**    | 10 classes: ``ContainerV2``, ``Section``,                | ``docs/extras/``       |
|                      | ``TextDisplay``, ``Thumbnail``, ``MediaGallery``,        | ``components-v2.md``   |
|                      | ``FileV2``, ``Seperator``, ``Modal`` and more            |                        |
+----------------------+----------------------------------------------------------+------------------------+
| **Soundboard**       | ``SoundboardSound``, six ``Guild`` methods,              | ``docs/extras/``       |
|                      | automatic trimming to 5 s / 512 KB                       | ``soundboard.md``      |
+----------------------+----------------------------------------------------------+------------------------+
| **Voice with DAVE**  | ``aead_xchacha20_poly1305_rtpsize``, MLS via ``davey``,  | ``docs/extras/``       |
|                      | voice gateway v8 — receiving works again                 | ``voice-dave.md``      |
+----------------------+----------------------------------------------------------+------------------------+
| **Flags and enums**  | ``is_component_v2``, ``has_snapshot``, new message       | ``docs/extras/``       |
|                      | types, application emojis                                | ``flags-and-enums.md`` |
+----------------------+----------------------------------------------------------+------------------------+

Full details: `docs/extras/README.md <docs/extras/README.md>`_

Two pitfalls up front
---------------------

.. warning::

    **1. ``Seperator`` is misspelled** — one ``a`` is missing.
    ``discord.Separator`` does not exist and raises ``AttributeError``. The
    typo stays on purpose: fixing it would break every existing call.

    **2. ``import discord`` requires pydub.** ``soundboard.py`` imports it at
    module level and ``guild.py`` imports ``soundboard``, so importing the
    whole library depends on it even when no sound is involved. ``pydub`` in
    turn shells out to **ffmpeg**.

Branches
--------

+------------------------------+------------------------------------------------------+
| ``developer-new-features``   | main branch of this fork — Components V2, Soundboard |
+------------------------------+------------------------------------------------------+
| ``dave-support``             | additionally voice support with DAVE                 |
+------------------------------+------------------------------------------------------+

Examples
--------

See the `examples <examples>`_ folder and the `upstream documentation
<https://discordpy-message-components.readthedocs.io/en/developer/>`_.

For the **additions** of this fork, complete examples live in
``docs/extras/`` — including a Components V2 layout taken from production
code.

Credits and license
-------------------

This fork is based on
`mccoderpy/discord.py-message-components <https://github.com/mccoderpy/discord.py-message-components>`_,
which itself builds on `discord.py <https://github.com/Rapptz/discord.py>`_
by Rapptz. License unchanged: **MIT** (see ``LICENSE``).

Bug reports about the **upstream project** belong there, not here:
`upstream issues <https://github.com/mccoderpy/discord.py-message-components/issues>`_
· `support server <https://discord.gg/sb69muSqsg>`_
