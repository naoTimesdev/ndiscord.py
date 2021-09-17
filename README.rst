🔧 Fork Notice
===============
This fork is made with `naoTimes <https://github.com/naoTimesdev/naoTimes>`_ in mind.

This fork will focus on improving and adding feature for the library.

What this fork does:

- Adding new feature like slash command, user command, and message command.
- Adding new feature that are in Discord canary or beta (as long as it's being documented in the API).
- PEP8 friendly, you can check the ``flake8`` and ``black`` configuration for more info.

What this fork does not do:

- Removing feature or doing radical changes to the project structure.

ndiscord.py
==========

.. image:: https://img.shields.io/github/last-commit/naoTimesdev/ndiscord.py.svg?color=blue
   :target: https://github.com/naoTimesdev/ndiscord.py/commits/master
   :alt: Last Commit
.. image:: https://img.shields.io/badge/python-3.8%20%7C%203.9-blue.svg
   :target: #
   :alt: Supported Python versions

A modern, easy to use, feature-rich, and async ready API wrapper for Discord written in Python.

The Future of discord.py
--------------------------

Rapptz has discontinued working on discord.py with reason you can read at this `gist <https://gist.github.com/Rapptz/4a2f62751b9600a31a0d3c78100287f1>`_.
This fork will not be "the new discord.py" but more like a discord.py that will be used for my own personal bot.

Key Features
-------------

- Modern Pythonic API using ``async`` and ``await``.
- Proper rate limit handling.
- Optimised in both speed and memory.
- Slash command, user context command, and message context command support.

Installing
----------

**Python 3.8 or higher is required**

You can only install this library by using development version:

.. code:: sh

    $ pip install -U git+https://github.com/naoTimesdev/ndiscord.py

or clone it manually:

.. code:: sh

    $ git clone https://github.com/naoTimesdev/ndiscord.py
    $ cd discord.py
    $ python3 -m pip install -U .[voice]


Optional Packages
~~~~~~~~~~~~~~~~~~

* `PyNaCl <https://pypi.org/project/PyNaCl/>`__ (for voice support)

Please note that on Linux installing voice you must install the following packages via your favourite package manager (e.g. ``apt``, ``dnf``, etc) before running the above commands:

* libffi-dev (or ``libffi-devel`` on some systems)
* python-dev (e.g. ``python3.6-dev`` for Python 3.6)

Quick Example
--------------

.. code:: py

    import discord

    class MyClient(discord.Client):
        async def on_ready(self):
            print('Logged on as', self.user)

        async def on_message(self, message):
            # don't respond to ourselves
            if message.author == self.user:
                return

            if message.content == 'ping':
                await message.channel.send('pong')

    client = MyClient()
    client.run('token')

Bot Example
~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix='>')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('token')

You can find more examples in the examples directory.

Slash Command Example
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: py
   
    import discord
    from discord.ext import app, commands
   
    bot = commands.Bot(command_prefix='n!')
   
    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')
      
    @app.slash_command()
    @app.option('content', str)
    async def echo(ctx, content):
        await ctx.send(content)
        
    bot.run('token')

Links
------

- `Documentation <https://discordpy.readthedocs.io/en/latest/index.html>`_
- `Discord API Server <https://discord.gg/discord-api>`_
