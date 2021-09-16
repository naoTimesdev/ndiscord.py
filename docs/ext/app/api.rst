.. currentmodule:: discord

API Reference
===============

The following section outlines the API of discord.py's application extension module.

.. _ext_app_api_core:

Core Functions
-----------------

ApplicationCommand
~~~~~~~~~~~~~~~~~~~~

.. attributetable:: discord.ext.app.ApplicationCommand

.. autoclass:: discord.ext.app.ApplicationCommand
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, error

    .. automethod:: ApplicationCommand.after_invoke()
        :decorator:

    .. automethod:: ApplicationCommand.before_invoke()
        :decorator:

    .. automethod:: ApplicationCommand.error()
        :decorator:

ContextMenuApplication
~~~~~~~~~~~~~~~~~~~~~~~

.. attributetable:: discord.ext.app.ContextMenuApplication

.. autoclass:: discord.ext.app.ContextMenuApplication
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, error

    .. automethod:: ContextMenuApplication.after_invoke()
        :decorator:

    .. automethod:: ContextMenuApplication.before_invoke()
        :decorator:

    .. automethod:: ContextMenuApplication.error()
        :decorator:

SlashCommand
~~~~~~~~~~~~~

.. attributetable:: discord.ext.app.SlashCommand

.. autoclass:: discord.ext.app.SlashCommand
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, error, command, group

    .. automethod:: SlashCommand.after_invoke()
        :decorator:

    .. automethod:: SlashCommand.before_invoke()
        :decorator:

    .. automethod:: SlashCommand.error()
        :decorator:

    .. automethod:: SlashCommand.command()
        :decorator:

    .. automethod:: SlashCommand.group()
        :decorator:

UserCommand
~~~~~~~~~~~~

.. attributetable:: discord.ext.app.UserCommand

.. autoclass:: discord.ext.app.UserCommand
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, error

    .. automethod:: UserCommand.after_invoke()
        :decorator:

    .. automethod:: UserCommand.before_invoke()
        :decorator:

    .. automethod:: UserCommand.error()
        :decorator:

MessageCommand
~~~~~~~~~~~~~~~

.. attributetable:: discord.ext.app.MessageCommand

.. autoclass:: discord.ext.app.MessageCommand
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, error

    .. automethod:: MessageCommand.after_invoke()
        :decorator:

    .. automethod:: MessageCommand.before_invoke()
        :decorator:

    .. automethod:: MessageCommand.error()
        :decorator:

Decorators
~~~~~~~~~~~

This is all available decorators that user can use to create application command.

.. autofunction:: discord.ext.app.application_command
    :decorator:

.. autofunction:: discord.ext.app.slash_command
    :decorator:

.. autofunction:: discord.ext.app.user_command
    :decorator:

.. autofunction:: discord.ext.app.message_command
    :decorator:

.. autofunction:: discord.ext.app.command
    :decorator:


.. _ext_app_api_mixins:

Mixins
-------

This is information for Mixins created to help load applications into the Bot or Client.

.. warning::

    You should not create all of this mixins manually if you don't know what you're doing.

ApplicationCommandMixin
~~~~~~~~~~~~~~~~~~~~~~~~

.. attributetable:: discord.ext.app.ApplicationCommandMixin

.. autoclass:: discord.ext.app.ApplicationCommandMixin
    :members:
    :exclude-members: application_command, slash_command, user_command, message_command

    .. automethod:: ApplicationCommandMixin.application_command(*args, **kwargs)
        :decorator:

    .. automethod:: ApplicationCommandMixin.slash_command(*args, **kwargs)
        :decorator:

    .. automethod:: ApplicationCommandMixin.user_command(*args, **kwargs)
        :decorator:

    .. automethod:: ApplicationCommandMixin.message_command(*args, **kwargs)
        :decorator:

ApplicationCommandFactory
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. attributetable:: discord.ext.app.mixins.ApplicationCommandFactory

.. autoclass:: discord.ext.app.mixins.ApplicationCommandFactory
    :members:


.. _ext_app_api_event:

Event Reference
-----------------

These events function similar to :ref:`the regular events <discord-api-events>`, except they
are custom to the app extension module.

.. function:: discord.ext.app.on_application_error(ctx, error)

    An error handler that is called when an error is raised
    inside a command either through user input error, check
    failure, or an error in your own code.

    :param ctx: The invocation context.
    :type ctx: :class:`.ApplicationContext`
    :param error: The error that was raised.
    :type error: :class:`.ApplicationCommandError` derived

.. function:: discord.ext.app.on_application(ctx)

    An event that is called when a command is found and is about to be invoked.

    This event is called regardless of whether the command itself succeeds via
    error or completes.

    :param ctx: The invocation context.
    :type ctx: :class:`.ApplicationContext`

.. function:: discord.ext.app.on_application_completion(ctx)

    An event that is called when a command has completed its invocation.

    This event is called only if the command succeeded, i.e. all checks have
    passed and the user input it correctly.

    :param ctx: The invocation context.
    :type ctx: :class:`.ApplicationContext`

.. function:: discord.ext.app.on_unknown_application(interaction)

    An event that is called if an unknown command is invoked.

    This event is called just after the Bot try to find matching command.

    :param ctx: The interaction context.
    :type ctx: :class:`Interaction`


.. _ext_app_api_checks:

Checks
-------

.. autofunction:: discord.ext.app.check(predicate)
    :decorator:

.. autofunction:: discord.ext.app.check_any(*checks)
    :decorator:

.. autofunction:: discord.ext.app.has_role(item)
    :decorator:

.. autofunction:: discord.ext.app.bot_has_role(**perms)
    :decorator:

.. autofunction:: discord.ext.app.has_any_role(*items)
    :decorator:

.. autofunction:: discord.ext.app.bot_has_any_role(*items)
    :decorator:

.. autofunction:: discord.ext.app.has_permissions(**perms)
    :decorator:

.. autofunction:: discord.ext.app.bot_has_permissions(**perms)
    :decorator:

.. autofunction:: discord.ext.app.has_guild_permissions(**perms)
    :decorator:

.. autofunction:: discord.ext.app.bot_has_guild_permissions(**perms)
    :decorator:

.. autofunction:: discord.ext.app.dm_only()
    :decorator:

.. autofunction:: discord.ext.app.guild_only()
    :decorator:

.. autofunction:: discord.ext.app.is_owner()
    :decorator:

.. autofunction:: discord.ext.app.is_nsfw()
    :decorator:

.. autofunction:: discord.ext.app.before_invoke(coro)
    :decorator:

.. autofunction:: discord.ext.app.after_invoke(coro)
    :decorator:

.. _ext_app_api_context:

Context
---------

.. attributetable:: discord.ext.app.ApplicationContext

.. autoclass:: discord.ext.app.ApplicationContext
    :members:
    :inherited-members:
    :exclude-members: history, typing

    .. automethod:: discord.ext.commands.Context.history
        :async-for:

    .. automethod:: discord.ext.commands.Context.typing
        :async-with:

.. _ext_app_api_errors:

Exceptions
-----------

.. autoexception:: discord.ext.app.ApplicationCommandError
    :members:

.. autoexception:: discord.ext.app.ApplicationCommandInvokeError
    :members:

.. autoexception:: discord.ext.app.ApplicationRegistrationError
    :members:

.. autoexception:: discord.ext.app.ApplicationRegistrationMaxDepthError
    :members:

.. autoexception:: discord.ext.app.ApplicationRegistrationExistingParentOptions
    :members:

.. autoexception:: discord.ext.app.ApplicationCheckFailure
    :members:

.. autoexception:: discord.ext.app.ApplicationCheckAnyFailure
    :members:

.. autoexception:: discord.ext.app.ApplicationPrivateMessageOnly
    :members:

.. autoexception:: discord.ext.app.ApplicationNoPrivateMessage
    :members:

.. autoexception:: discord.ext.app.ApplicationMissingRole
    :members:

.. autoexception:: discord.ext.app.ApplicationBotMissingRole
    :members:

.. autoexception:: discord.ext.app.ApplicationMissingAnyRole
    :members:

.. autoexception:: discord.ext.app.ApplicationBotMissingAnyRole
    :members:

.. autoexception:: discord.ext.app.ApplicationMissingPermissions
    :members:

.. autoexception:: discord.ext.app.ApplicationBotMissingPermissions
    :members:

.. autoexception:: discord.ext.app.ApplicationNSFWChannelRequired
    :members:

.. autoexception:: discord.ext.app.ApplicationNotOwner
    :members:

Exception Hierarchy
~~~~~~~~~~~~~~~~~~~~~

.. exception_hierarchy::

    - :exc:`~.DiscordException`
        - :exc:`~.app.ApplicationCommandError`
            - :exc:`~.app.ApplicationCommandInvokeError`
            - :exc:`~.app.ApplicationCheckFailure`
                - :exc:`~.app.ApplicationCheckAnyFailure`
                - :exc:`~.app.ApplicationPrivateMessageOnly`
                - :exc:`~.app.ApplicationNoPrivateMessage`
                - :exc:`~.app.ApplicationMissingRole`
                - :exc:`~.app.ApplicationBotMissingRole`
                - :exc:`~.app.ApplicationMissingAnyRole`
                - :exc:`~.app.ApplicationBotMissingAnyRole`
                - :exc:`~.app.ApplicationMissingPermissions`
                - :exc:`~.app.ApplicationBotMissingPermissions`
                - :exc:`~.app.ApplicationNSFWChannelRequired`
                - :exc:`~.app.ApplicationNotOwner`
    - :exc:`~.ClientException`
        - :exc:`~.app.ApplicationRegistrationError`
        - :exc:`~.app.ApplicationRegistrationMaxDepthError`
        - :exc:`~.app.ApplicationRegistrationExistingParentOptions`
