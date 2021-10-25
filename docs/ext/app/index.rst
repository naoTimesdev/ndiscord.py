.. _discord_ext_app:

``discord.ext.app`` -- An application command extension
===========================================================================

.. versionadded:: 2.0.0

``ndiscord.py`` fork have a native support for slash command and more. User or developer can develop their own version
by intercepting the ``on_interaction`` event and handling the error. But, we made it simple
so developer can just use this to obviously create a easy slash command without worrying much.

This app framework follows closely the ``discord.ext.commands`` framework.

.. toctree::
    :maxdepth: 2

    usage
    autocomplete
    api
