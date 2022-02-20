"""
The MIT License (MIT)

Copyright (c) 2021-present noaione, Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations
import inspect
import os
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Type, TypeVar

from ..components import TextInput as TextInputComponent
from ..enums import TextInputStyle, ComponentType
from .item import Item, ItemCallbackType

__all__ = (
    "Text",
    "text_input",
)

if TYPE_CHECKING:
    from .view import View

TX = TypeVar("TX", bound="Text")
V = TypeVar("V", bound="View", covariant=True)


class Text(Item[V]):
    """Represents a UI text input.

    .. versionadded:: 2.0

    Parameters
    ------------
    style: :class:`discord.TextInputStyle`
        The style of the text input.
    custom_id: :class:`str`
        The ID of the text input that gets received during an interaction.
    label: :class:`str`
        The label for this component.
    required: :class:`bool`
        Whether this component is required to be filled, default to ``True``
    min_length: Optional[:class:`int`]
        The minimum input length for a text input.
        Defaults to ``None`` and must be between 0 to 4000.
    max_length: Optional[:class:`int`]
        The maximum input length for a text input.
        Defaults to ``None`` and must be between 1 to 4000.
    value: Optional[:class:`str`]
        A pre-filled value for this component, max 4000 characters.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if text input is empty.
    """

    __item_repr_attributes__: Tuple[str, ...] = (
        "style",
        "label",
        "required",
    )

    def __init__(
        self,
        *,
        style: TextInputStyle,
        label: str,
        custom_id: Optional[str] = None,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        value: Optional[str] = None,
        placeholder: Optional[str] = None,
    ):
        super().__init__()
        self._provided_custom_id = custom_id is not None
        if custom_id is None:
            custom_id = os.urandom(16).hex()

        self._underlying = TextInputComponent._raw_construct(
            type=ComponentType.text_input,
            style=style,
            custom_id=custom_id,
            label=label,
            required=required,
            min_length=min_length,
            max_length=max_length,
            value=value,
            placeholder=placeholder,
        )

    @property
    def style(self) -> TextInputStyle:
        """:class:`discord.TextInputStyle`: The style of the text input."""
        return self._underlying.style

    @style.setter
    def style(self, value: TextInputStyle):
        self._underlying.style = value

    @property
    def custom_id(self) -> str:
        """:class:`str`: The ID of the text input that gets received during an interaction."""
        return self._underlying.custom_id

    @custom_id.setter
    def custom_id(self, value: str):
        self._underlying.custom_id = value

    @property
    def label(self) -> str:
        """:class:`str`: The label for this component."""
        return self._underlying.label

    @label.setter
    def label(self, value: str):
        self._underlying.label = value

    @property
    def required(self) -> bool:
        """:class:`bool`: Whether this component is required to be filled."""
        return self._underlying.required

    @required.setter
    def required(self, value: bool):
        self._underlying.required = value

    @property
    def min_length(self) -> Optional[int]:
        """Optional[:class:`int`]: The minimum input length for a text input.

        Defaults to ``None`` and must be between 0 to 4000.
        """
        return self._underlying.min_length

    @min_length.setter
    def min_length(self, value: Optional[int]):
        if value is not None and not isinstance(value, int):
            raise TypeError("min_length must be None or int")
        self._underlying.min_length = value

    @property
    def max_length(self) -> Optional[int]:
        """Optional[:class:`int`]: The maximum input length for a text input.

        Defaults to ``None`` and must be between 1 to 4000.
        """
        return self._underlying.max_length

    @max_length.setter
    def max_length(self, value: Optional[int]):
        if value is not None and not isinstance(value, int):
            raise TypeError("max_length must be None or int")
        self._underlying.max_length = value

    @property
    def value(self) -> Optional[str]:
        """Optional[:class:`str`]: A pre-filled value for this component, max 4000 characters."""
        return self._underlying.value

    @value.setter
    def value(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise TypeError("value must be None or str")
        self._underlying.value = value

    @property
    def placeholder(self) -> Optional[str]:
        """Optional[:class:`str`]: The placeholder text that is shown if text input is empty."""
        return self._underlying.placeholder

    @placeholder.setter
    def placeholder(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise TypeError("placeholder must be None or str")
        self._underlying.placeholder = value

    @classmethod
    def from_component(cls: Type[TX], component: TextInputComponent) -> TX:
        return cls(
            style=component.style,
            label=component.label,
            custom_id=component.custom_id,
            required=component.required,
            min_length=component.min_length,
            max_length=component.max_length,
            value=component.value,
            placeholder=component.placeholder,
        )

    @property
    def type(self) -> ComponentType:
        return self._underlying.type

    def to_component_dict(self):
        return self._underlying.to_dict()

    def refresh_component(self, component: TextInputComponent) -> None:
        self._underlying = component

    def is_dispatchable(self) -> bool:
        return self.custom_id is not None


def text_input(
    *,
    label: str,
    style: TextInputStyle = TextInputStyle.short,
    custom_id: Optional[str] = None,
    required: bool = True,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    value: Optional[str] = None,
    placeholder: Optional[str] = None,
) -> Callable[[ItemCallbackType], ItemCallbackType]:
    """A decorator that attaches a text input to a component.

    The function being decorated should have three parameters, ``self`` representing
    the :class:`discord.ui.View`, the :class:`discord.ui.Text` being pressed and
    the :class:`discord.Interaction` you receive.

    Parameters
    ------------
    label: :class:`str`
        The label for the component.
    style: :class:`discord.TextInputStyle`
        The style of the text input.
    custom_id: Optional[:class:`str`]
        The ID of the text input that gets received during an interaction.
        If ``None``, it will be auto generated.
    required: :class:`bool`
        Whether the component is required to be filled, default to ``True``
    min_length: Optional[:class:`int`]
        The minimum input length for a text input.
        Defaults to ``None`` and must be between 0 to 4000.
    max_length: Optional[:class:`int`]
        The maximum input length for a text input.
        Defaults to ``None`` and must be between 1 to 4000.
    value: Optional[:class:`str`]
        A pre-filled value for the component, max 4000 characters.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if text input is empty.
    """

    def decorator(func: ItemCallbackType) -> ItemCallbackType:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("text_input function must be a coroutine function")

        func.__discord_ui_model_type__ = Text
        func.__discord_ui_model_kwargs__ = {
            "label": label,
            "style": style,
            "custom_id": custom_id,
            "required": required,
            "min_length": min_length,
            "max_length": max_length,
            "value": value,
            "placeholder": placeholder,
        }
        return func

    return decorator
