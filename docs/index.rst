:og:title: discord4py (fork) documentation
:og:description: Personal fork of discord.py-message-components with Components V2, Soundboard and DAVE voice support

discord4py — personal fork
==========================

.. image:: https://readthedocs.org/projects/discord4py-fork/badge/?version=latest
   :target: https://discord4py-fork.readthedocs.io/en/latest/
   :alt: Documentation status

A fork of `discord.py-message-components <https://github.com/mccoderpy/discord.py-message-components>`_
by `mccoderpy <https://github.com/mccoderpy/>`_, which itself builds on
`discord.py <https://github.com/Rapptz/discord.py>`_ by `Rapptz <https://github.com/Rapptz>`_.

Maintained by `Cyber-Frodo <https://github.com/Cyber-Frodo>`_ ·
`Repository <https://github.com/Cyber-Frodo/discord.py-message-components>`_

.. important::

    **Install from this fork, not from upstream.** The upstream install
    command replaces this version and removes everything listed under
    :doc:`Fork extras <extras/README>` — Components V2, Soundboard and DAVE
    voice support. Bots relying on those break with ``AttributeError``.

Installation
------------

.. code:: sh

    # Windows
    py -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"

    # Linux / Raspberry Pi
    python3 -m pip install -U "git+https://github.com/Cyber-Frodo/discord.py-message-components.git@developer-new-features"

With voice support (branch ``dave-support``):

.. code:: sh

    py -m pip install -U "discord.py-message-components[voice] @ git+https://github.com/Cyber-Frodo/discord.py-message-components.git@dave-support"

The ``voice`` extra pulls ``PyNaCl>=1.5.0,<1.6`` and ``davey>=0.1.6``. Both
bounds are mandatory — see :doc:`extras/voice-dave`.

.. note::

    This library overrides ``import discord``. Uninstall ``discord.py``
    first if it is present.

What this fork adds
-------------------

Four areas on top of upstream, all documented under :doc:`Fork extras <extras/README>`:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Area
     - Contents
   * - :doc:`Components V2 <extras/components-v2>`
     - ``ContainerV2``, ``Section``, ``TextDisplay``, ``Thumbnail``,
       ``MediaGallery``, ``FileV2``, ``Seperator``, ``Modal`` and more
   * - :doc:`Soundboard <extras/soundboard>`
     - ``SoundboardSound``, six ``Guild`` methods, automatic trimming to
       5 s / 512 KB
   * - :doc:`Voice with DAVE <extras/voice-dave>`
     - ``aead_xchacha20_poly1305_rtpsize``, MLS via ``davey``, voice gateway
       v8 — receiving works again
   * - :doc:`Flags and enums <extras/flags-and-enums>`
     - ``is_component_v2``, ``has_snapshot``, new message types, application
       emojis

Features
--------

Inherited from upstream:

- Modern Pythonic API using ``async``\/``await`` syntax
- Sane rate limit handling that prevents 429s
- Implements the entire Discord API
- Command extension to aid with bot creation
- Buttons addressed via ``custom_id`` instead of ``View`` — they keep working
  after a restart, because no state lives in process memory

Getting started
---------------

- **First steps:** :doc:`intro` | :doc:`quickstart` | :doc:`logging`
- **Working with Discord:** :doc:`discord` | :doc:`intents`
- **Fork-specific:** :doc:`extras/README`

Getting help
------------

- The :doc:`faq` covers the common questions.
- Issues about **upstream behaviour** belong in the
  `upstream tracker <https://github.com/mccoderpy/discord.py-message-components/issues>`_
  or the `support server <https://discord.gg/sb69muSqsg>`_.
- Issues about the **additions listed above** belong in
  `this fork's tracker <https://github.com/Cyber-Frodo/discord.py-message-components/issues>`_.

Fork extras
-----------

What this fork adds on top of upstream — Components V2, Soundboard and
voice support with DAVE.

.. toctree::
  :maxdepth: 1

  Overview <extras/README.md>
  extras/components-v2.md
  extras/soundboard.md
  extras/voice-dave.md
  extras/flags-and-enums.md

Extensions
----------

These extensions help you during development when it comes to common tasks.

.. toctree::
  :maxdepth: 1

  ext/commands/index.rst
  ext/tasks/index.rst

Manuals
-------

These pages go into great detail about everything the API can do.

.. toctree::
  :maxdepth: 1

  API Reference </api/index.rst>
  Interactions <Interactions/index.rst>
  OAuth2 <oauth2/index.rst>
  discord.ext.commands API Reference <ext/commands/api.rst>
  discord.ext.tasks API Reference <ext/tasks/index.rst>

Meta
----

If you're looking for something related to the project itself, it's here.

.. toctree::
    :maxdepth: 1

    whats_new
    version_guarantees
    migrating
    migrating_to_async

License
-------

MIT — see ``LICENSE``. The copyright notices of Rapptz and mccoderpy remain
in place; this fork adds to their work rather than replacing it.
