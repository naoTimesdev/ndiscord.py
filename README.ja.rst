ð§ ãç¥ãã
===========
ãã®ãã©ã¼ã¯ã¯ãç¹ã«naoTimesã®ããã«ä½ããããã®ã§ãã

ãã®ãã©ã¼ã¯ã§ã¯ãã¢ããªã±ã¼ã·ã§ã³(Slash/User/Message)ã®ãããªæ©è½ã®éçºã¨ãPRã«ããæ©è½ã®è¿½å ã«ç¦ç¹ãå½ã¦ã¾ãã
ãã®ãªãã¸ããªãèªåã®ãããã«ä½¿ããã¨ã¯ã¾ã ãå§ãã§ãã¾ããã

ndiscord.py
==========

.. image:: https://discord.com/api/guilds/336642139381301249/embed.png
   :target: https://discord.gg/nXzj3dg
   :alt: Discordãµã¼ãã¼ã®æå¾
.. image:: https://img.shields.io/pypi/v/discord.py.svg
   :target: https://pypi.python.org/pypi/discord.py
   :alt: PyPIã®ãã¼ã¸ã§ã³æå ±
.. image:: https://img.shields.io/pypi/pyversions/discord.py.svg
   :target: https://pypi.python.org/pypi/discord.py
   :alt: PyPIã®ãµãã¼ããã¦ããPythonã®ãã¼ã¸ã§ã³

ndiscord.py ã¯æ©è½è±å¯ãã¤ã¢ãã³ã§ä½¿ãããããéåæå¦çã«ãå¯¾å¿ããDiscordç¨ã®APIã©ããã¼ã§ãã

ä¸»ãªç¹å¾´
-------------

- ``async`` ã¨ ``await`` ãä½¿ã£ãã¢ãã³ãªPythonãããAPIã
- é©åãªã¬ã¼ãå¶éå¦ç
- ã¡ã¢ãªã¨éåº¦ã®ä¸¡æ¹ãæé©åã
- ã¹ã©ãã·ã¥ã³ãã³ããã¦ã¼ã¶ã¼ã³ãã³ããã¡ãã»ã¼ã¸ã³ãã³ãã«å¯¾å¿ã

ã¤ã³ã¹ãã¼ã«
-------------

**Python 3.8 ä»¥éã®ãã¼ã¸ã§ã³ãå¿é ã§ã**

ãã®ã©ã¤ãã©ãªã¯ãéçºãã¼ã¸ã§ã³ãä½¿ç¨ãã¦ã®ã¿ã¤ã³ã¹ãã¼ã«ã§ãã¾ã:

.. code:: sh

    $ pip install -U git+https://github.com/naoTimesdev/ndiscord.py

é³å£°ãµãã¼ããå¿è¦ãªããæ¬¡ã®ã³ãã³ããå®è¡ãã¾ããã:

.. code:: sh

    # Linux/OS X
    python3 -m pip install -U discord.py[voice]

    # Windows
    py -3 -m pip install -U discord.py[voice]


èªåã§ãªãã¸ããªãã¯ã­ã¼ã³ãã:

.. code:: sh

    $ git clone https://github.com/naoTimesdev/ndiscord.py
    $ cd discord.py
    $ python3 -m pip install -U .[voice]


ãªãã·ã§ã³ããã±ã¼ã¸
~~~~~~~~~~~~~~~~~~~~~~

* PyNaCl (é³å£°ãµãã¼ãç¨)

Linuxã§é³å£°ãµãã¼ããå°å¥ããã«ã¯ãåè¿°ã®ã³ãã³ããå®è¡ããåã«ãæ°ã«å¥ãã®ããã±ã¼ã¸ããã¼ã¸ã£ã¼(ä¾ãã° ``apt`` ã ``dnf`` ãªã©)ãä½¿ã£ã¦ä»¥ä¸ã®ããã±ã¼ã¸ãã¤ã³ã¹ãã¼ã«ããå¿è¦ãããã¾ã:

* libffi-dev (ã·ã¹ãã ã«ãã£ã¦ã¯ ``libffi-devel``)
* python-dev (ä¾ãã°Python 3.6ç¨ã® ``python3.6-dev``)

ç°¡åãªä¾
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

Botã®ä¾
~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix='>')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('token')

examplesãã£ã¬ã¯ããªã«æ´ã«å¤ãã®ãµã³ãã«ãããã¾ãã

ãªã³ã¯
------

- `ãã­ã¥ã¡ã³ã <https://discordpy.readthedocs.io/ja/latest/index.html>`_
- `Discord API <https://discord.gg/discord-api>`_
