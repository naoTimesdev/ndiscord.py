.. currentmodule:: discord

.. TODO: Restructure this docs.

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

    # or
    
    @app.slash_command(name="Louder")
    async def echo(ctx, text: Option(str, description="This is a description")):
        # This will set `text` to string type.
        # And give "This is a description" description
        await ctx.send(text.upper())

The :func:`~ext.app.option` decorator parameter is optional if you use typing.
But if you want to adjust it manually you should use it.

The first parameter would be the variable name that you want to change, while the second one
is the type. You can also use the :class:`~enums.SlashCommandOptionType` for the 2nd parameter.

Everything else are optional.

.. _ext_app_usage_error_handler:

Error Handling
----------------

When our commands fail to parse we will, by default, receive a noisy error in ``stderr`` of our console that tells us
that an error has happened and has been silently ignored.

In order to handle our errors, we must use something called an error handler. There is a global error handler, called
:func:`.on_application_error` which works like any other event in the :ref:`discord-api-events`. This global error handler is
called for every error reached.

App extension also includes their own :ref:`ext_app_api_event` that you can check out.

Most of the time however, we want to handle an error local to the command itself. Luckily, commands come with local error
handlers that allow us to do just that. First we decorate an error handler function with :meth:`.ApplicationCommand.error`:

.. code-block:: python3

    @app.command()
    async def info(ctx, member: discord.Member):
        """Tells you some info about the member."""
        msg = f'{member} joined on {member.joined_at} and has {len(member.roles)} roles.'
        await ctx.send(msg)

    @info.error
    async def info_error(ctx, error):
        if isinstance(error, app.ApplicationCheckFailure):
            await ctx.send('I could not find that member...')

The first parameter of the error handler is the :class:`.ApplicationContext` while the second one is an exception that is derived from
:exc:`~ext.app.ApplicationCommandError`. A list of errors is found in the :ref:`ext_app_api_errors` page of the documentation.

Checks
-------

The application command can also use checks to make sure some stuff is working as intended.
It follow closely how ext.commands works.

You just need to use the :func:`~ext.app.check` decorator to define a check.
You can also invoke :func:`~ext.app.before_invoke` and :func:`~ext.app.after_invoke` decorator.

A check is a basic predicate that can take in a :class:`.ApplicationContext` as its sole parameter. Within it, you have the following
options:

- Return ``True`` to signal that the person can run the command.
- Return ``False`` to signal that the person cannot run the command.
- Raise a :exc:`~ext.app.ApplicationCommandError` derived exception to signal the person cannot run the command.

    - This allows you to have custom error messages for you to handle in the
      :ref:`error handlers <ext_app_usage_error_handler>`.

To register a check for a command, we would have two ways of doing so. The first is using the :meth:`~ext.commands.check`
decorator. For example:

.. code-block:: python3

    async def is_owner(ctx):
        return ctx.author.id == 466469077444067372

    @app.command(name='eval')
    @app.check(is_owner)
    async def _eval(ctx, *, code):
        """A bad example of an eval command"""
        await ctx.send(eval(code))

This would only evaluate the command if the function ``is_owner`` returns ``True``. Sometimes we re-use a check often and
want to split it into its own decorator. To do that we can just add another level of depth:

.. code-block:: python3

    def is_owner():
        async def predicate(ctx):
            return ctx.author.id == 316026178463072268
        return app.check(predicate)

    @app.command(name='eval')
    @is_owner()
    async def _eval(ctx, *, code):
        """A bad example of an eval command"""
        await ctx.send(eval(code))

Since an owner check is so common, the library provides it for you (:func:`~ext.app.is_owner`):

.. code-block:: python3

    @bot.command(name='eval')
    @app.is_owner()
    async def _eval(ctx, *, code):
        """A bad example of an eval command"""
        await ctx.send(eval(code))

When multiple checks are specified, **all** of them must be ``True``:

.. code-block:: python3

    def is_in_guild(guild_id):
        async def predicate(ctx):
            return ctx.guild and ctx.guild.id == guild_id
        return app.check(predicate)

    @app.command()
    @app.is_owner()
    @is_in_guild(41771983423143937)
    async def secretguilddata(ctx):
        """super secret stuff"""
        await ctx.send('secret stuff')

If any of those checks fail in the example above, then the command will not be run.

When an error happens, the error is propagated to the :ref:`error handlers <ext_app_usage_error_handler>`. If you do not
raise a custom :exc:`~ext.app.ApplicationCommandError` derived exception, then it will get wrapped up into a
:exc:`~ext.app.ApplicationCheckFailure` exception as so:

.. code-block:: python3

    @app.command()
    @app.is_owner()
    @is_in_guild(41771983423143937)
    async def secretguilddata(ctx):
        """super secret stuff"""
        await ctx.send('secret stuff')

    @secretguilddata.error
    async def secretguilddata_error(ctx, error):
        if isinstance(error, app.ApplicationCheckFailure):
            await ctx.send('nothing to see here comrade.')

If you want a more robust error system, you can derive from the exception and raise it instead of returning ``False``:

.. code-block:: python3

    class NoPrivateMessages(app.ApplicationCheckFailure):
        pass

    def guild_only():
        async def predicate(ctx):
            if ctx.guild is None:
                raise NoPrivateMessages('Hey no DMs!')
            return True
        return app.check(predicate)

    @guild_only()
    async def test(ctx):
        await ctx.send('Hey this is not a DM! Nice.')

    @test.error
    async def test_error(ctx, error):
        if isinstance(error, NoPrivateMessages):
            await ctx.send(error)

.. note::

    Since having a ``guild_only`` decorator is pretty common, it comes built-in via :func:`~ext.commands.guild_only`.

Global Checks
++++++++++++++

Sometimes we want to apply a check to **every** command, not just certain commands. The library supports this as well
using the global check concept.

Global checks work similarly to regular checks except they are registered with the :meth:`.Bot.check` decorator.

For example, to block all DMs we could do the following:

.. code-block:: python3

    @bot.check
    async def globally_block_dms(ctx):
        return ctx.guild is not None

.. warning::

    Be careful on how you write your global checks, as it could also lock you out of your own bot.
