.. currentmodule:: discord

.. _ext_app_autocomplete:

Autocompletion
=================

This page will covers information about autocompletion support for slash command.

Autocompletion works by responding to a users typing a query for something and we (bot) responded
to it by a list of choices.

For quick example, here's how you can answer to an autocompletion:

.. code-block:: python3

    @app.slash_command()
    @app.option("word", str, autocomplete=True)
    async def guess(ctx, word: str):
        # .autocompleting should return the focused parameter name
        # so if user is autocompleting "word", it should be "word"
        # It can be none if nothing is being focused.
        if ctx.autocompleting == "word":
            await ctx.autocomplete(["a", "b", "c"])
            # OR
            await ctx.autocomplete([
                OptionChoice("A", "a"),
                OptionChoice("B", "b"),
            ])
            return

        await ctx.send(f"Word is: {word}")

That is just a simple way to answer to autocompletion interaction.
It will just keep sending ``a`` and ``b`` and ``c`` to user.

You can obviously create a autocompletion system on your bot, but we will just provide
a simple way to answer to autocompletion.

You can use either a string list of response, or using :class:`.OptionChoice` for more granular response.
You can also mix it up, the library will automatically convert it to :class:`dict` for responding to Discord.

Attributes
------------

With this changes, we introduced an attribute called :attr:`.ApplicationContext.autocompleting`.

That attribute will return the current parameter that need responding. If there's nothing need autocompletion
that attribute will be ``None``.

Limitations
-------------

- Autocompletion can only be done on option that use :class:`str` type.
- The choices response is currently limited to 25 choices, this is Discord side and would be subject to changes.
- If you enabled autocompletion, you cannot set ``choices`` on the :class:`.Option` decorator. It will raise :exc:`ValueError`.

