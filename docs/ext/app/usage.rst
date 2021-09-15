.. currentmodule:: discord

.. _ext_app_usage:

Usage
===========

This is a basic and simple way to implement your own slash command.

Slash command and other are defined by attaching a decorator to a regular Python function.
The command then would be invoking that command if it match the signature.

For example, here's a simple slash command:

.. code-block:: python3

    from discord.ext import app
    
    @app.slash_command()
    @app.option("text", str)
    async def echo(ctx, text: str):
        await ctx.send(text)

That slash command would create a command called ``echo``. You can use it like:

.. code-block:: none

    /echo hello world

This in turn would return ``hello world`` to user.

A command must always have at least one parameter, ``ctx``, which is the :class:`.ApplicationContext` as the first one.

There are only one way to register a slash command and other. By using :func:`~ext.app.slash_command` decorator.
There's other decorator like :func:`~ext.app.user_command` and :func:`~ext.app.message_command` which is just
a context slash command type that can only receive 2 parameters:

.. code-block:: python3

    from discord.ext import app

    @app.user_command(name="Say Name")
    async def say_name(ctx, member):
        # Member would be the member that are selected
        # It would return discord.Member class

        await ctx.send(f"That user name is: {member.name}")

    @app.message_command(name="Say Message")
    async def say_message(ctx, message):
        # Message would be the message that are selected
        # It would return discord.Message class

        await ctx.send(f"That message content is: {message.content}")

Any parameter that is accepted by the :class:`.ApplicationCommand` constructor can be passed into the decorator.
For example, to change the slash command name, you can do:

.. code-block:: python3

    from discord.ext import app

    @app.slash_command(name="Louder")
    async def echo(ctx, text: str):
        await ctx.send(text.upper())

This would change the slash command from ``echo`` to ``Louder``

Parameters
------------

Since we define commands by making Python functions, we also define the argument passing behaviour by the function
parameters.

This would only work on slash command where you can customize the option.
User and Message command is context-based, so you dont even need to pass it.

To create an option, you either use the :func:`~ext.app.option` decorator or just use the Python typing in the parameter.

.. code-block:: python3

    from discord.ext import app

    @app.slash_command(name="Louder")
    async def echo(ctx, text):
        # This will default to string type
        await ctx.send(text.upper())

    # or

    @app.slash_command(name="Louder")
    async def echo(ctx, text: int):
        # This will set `text` to integer.
        await ctx.send(text * 2)

    # or

    @app.slash_command(name="Louder")
    @app.option("text", str)
    async def echo(ctx, text):
        # This will set `text` to string.
        await ctx.send(text.upper())

The :func:`~ext.app.option` decorator parameter is optional if you use typing.
But if you want to adjust it manually you should use it.

The first parameter would be the variable name that you want to change, while the second one
is the type. You can also use the :class:`~enums.SlashCommandOptionType` for the 2nd parameter.

Everything else are optional.

Checks
-------

The application command can also use checks to make sure some stuff is working as intended.
It follow closely how ext.commands works.

You just need to use the :func:`~ext.commands.check` decorator to define a check.
You can also invoke :meth:`.before_invoke` and :meth:`.after_invoke` decorator.

TBW
