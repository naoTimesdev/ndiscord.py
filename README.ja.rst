🔧 お知らせ
===========
このフォークは、特にnaoTimesのために作られたものです。

このフォークでは、アプリケーション(Slash/User/Message)のような機能の開発と、PRにある機能の追加に焦点を当てます。
このリポジトリを自分のボットに使うことはまだお勧めできません。

ndiscord.py
==========

.. image:: https://discord.com/api/guilds/336642139381301249/embed.png
   :target: https://discord.gg/nXzj3dg
   :alt: Discordサーバーの招待
.. image:: https://img.shields.io/pypi/v/discord.py.svg
   :target: https://pypi.python.org/pypi/discord.py
   :alt: PyPIのバージョン情報
.. image:: https://img.shields.io/pypi/pyversions/discord.py.svg
   :target: https://pypi.python.org/pypi/discord.py
   :alt: PyPIのサポートしているPythonのバージョン

ndiscord.py は機能豊富かつモダンで使いやすい、非同期処理にも対応したDiscord用のAPIラッパーです。

主な特徴
-------------

- ``async`` と ``await`` を使ったモダンなPythonらしいAPI。
- 適切なレート制限処理
- メモリと速度の両方を最適化。
- スラッシュコマンド、ユーザーコマンド、メッセージコマンドに対応。

インストール
-------------

**Python 3.8 以降のバージョンが必須です**

このライブラリは、開発バージョンを使用してのみインストールできます:

.. code:: sh

    $ pip install -U git+https://github.com/naoTimesdev/ndiscord.py

音声サポートが必要なら、次のコマンドを実行しましょう:

.. code:: sh

    # Linux/OS X
    python3 -m pip install -U discord.py[voice]

    # Windows
    py -3 -m pip install -U discord.py[voice]


自分でリポジトリをクローンする:

.. code:: sh

    $ git clone https://github.com/naoTimesdev/ndiscord.py
    $ cd discord.py
    $ python3 -m pip install -U .[voice]


オプションパッケージ
~~~~~~~~~~~~~~~~~~~~~~

* PyNaCl (音声サポート用)

Linuxで音声サポートを導入するには、前述のコマンドを実行する前にお気に入りのパッケージマネージャー(例えば ``apt`` や ``dnf`` など)を使って以下のパッケージをインストールする必要があります:

* libffi-dev (システムによっては ``libffi-devel``)
* python-dev (例えばPython 3.6用の ``python3.6-dev``)

簡単な例
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

Botの例
~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix='>')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('token')

examplesディレクトリに更に多くのサンプルがあります。

リンク
------

- `ドキュメント <https://discordpy.readthedocs.io/ja/latest/index.html>`_
- `Discord API <https://discord.gg/discord-api>`_
