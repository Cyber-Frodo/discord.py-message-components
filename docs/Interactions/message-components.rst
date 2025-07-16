.. currentmodule:: discord

ActionRow
~~~~~~~~~~

.. attributetable:: ActionRow

.. autoclass:: ActionRow()
    :members:

-----------------------

Button
~~~~~~~

.. attributetable:: Button

.. autoclass:: Button()
    :members:
    :inherited-members:

-----------------------

.. _select-like-objects:

SelectMenu
~~~~~~~~~~~

.. attributetable:: SelectMenu

.. autoclass:: SelectMenu()
    :members:
    :inherited-members:

SelectOption
~~~~~~~~~~~~~

.. attributetable:: SelectOption

.. autoclass:: SelectOption()
    :members:

SelectDefaultValue
~~~~~~~~~~~~~~~~~~~~

.. attributetable:: SelectDefaultValue

.. autoclass:: SelectDefaultValue()
    :members:

UserSelect
~~~~~~~~~~~

.. attributetable:: UserSelect

.. autoclass:: UserSelect()
    :members:
    :inherited-members:

RoleSelect
~~~~~~~~~~~

.. attributetable:: RoleSelect

.. autoclass:: RoleSelect()
    :members:
    :inherited-members:

MentionableSelect
~~~~~~~~~~~~~~~~~~

.. attributetable:: MentionableSelect

.. autoclass:: MentionableSelect()
    :members:
    :inherited-members:

ChannelSelect
~~~~~~~~~~~~~~

.. attributetable:: ChannelSelect

.. autoclass:: ChannelSelect()
    :members:
    :inherited-members:

----------------------------

Modal
~~~~~~

.. attributetable:: Modal

.. autoclass:: Modal()
    :members:
    :inherited-members:


TextInput
~~~~~~~~~~

.. attributetable:: TextInput

.. autoclass:: TextInput()
    :members:
    :inherited-members:

----------------------------

.. _component-v2-objects:

Section
~~~~~~~~

.. attributetable:: Section

.. autoclass:: Section
    :members:
    :show-inheritance:

    .. note::
        The ``components`` and ``accessory`` parameters can be passed as positional arguments.
        Example::

            Section([TextDisplay("foo")], Thumbnail("https://..."))

TextDisplay
~~~~~~~~~~~

.. attributetable:: TextDisplay

.. autoclass:: TextDisplay
    :members:
    :show-inheritance:

    .. note::
        ``content`` is a positional argument, ``id`` is optional.

Thumbnail
~~~~~~~~~

.. attributetable:: Thumbnail

.. autoclass:: Thumbnail
    :members:
    :show-inheritance:

    .. note::
        ``media`` is a positional argument, other parameters are optional.

MediaGallery
~~~~~~~~~~~~

.. attributetable:: MediaGallery

.. autoclass:: MediaGallery
    :members:
    :show-inheritance:

    .. note::
        ``items`` is a positional argument, ``id`` is optional.

FileV2
~~~~~~

.. attributetable:: FileV2

.. autoclass:: FileV2
    :members:
    :show-inheritance:

    .. note::
        ``file`` is a positional argument, other parameters are optional.

Seperator
~~~~~~~~~

.. attributetable:: Seperator

.. autoclass:: Seperator
    :members:
    :show-inheritance:

    .. note::
        ``divider`` and ``spacing`` are positional arguments, ``id`` is optional.

ContainerV2
~~~~~~~~~~~

.. attributetable:: ContainerV2

.. autoclass:: ContainerV2
    :members:
    :show-inheritance:

    .. note::
        ``components`` is a positional argument, other parameters are optional.
