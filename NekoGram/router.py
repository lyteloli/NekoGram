from typing import Callable, Optional, Union, Dict, Any, Awaitable
from aiogram import types

from .base_neko import BaseNeko
from .logger import LOGGER
from .menus import Menu


class NekoRouter:
    def __init__(self, name: Optional[str] = None):
        self.functions: Dict[str, Callable[
            [Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Awaitable[Any]
        ]] = dict()
        self.format_functions: Dict[str, Callable[[Menu, types.User, BaseNeko], Awaitable[Any]]] = dict()
        self.prev_menu_handlers: Dict[str, Callable[[Menu], Awaitable[str]]] = dict()
        self.next_menu_handlers: Dict[str, Callable[[Menu], Awaitable[str]]] = dict()
        self.name = name
        self._was_attached: bool = False

    def register_formatter(
            self, callback: Callable[[Menu, types.User, BaseNeko], Awaitable[Any]], name: Optional[str] = None
    ):
        """
        Register a formatter.
        :param callback: A formatter to call.
        :param name: Menu name.
        """
        self.format_functions[name or callback.__name__] = callback

    def formatter(self, name: Optional[str] = None):
        """
        Register a formatter.
        :param name: Menu name.
        """

        def decorator(callback: Callable[[Menu, types.User, BaseNeko], Awaitable[Any]]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(
            self,
            callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Awaitable[Any]],
            name: Optional[str] = None
    ):
        """
        Register a function.
        :param callback: A function to call.
        :param name: Menu name.
        """
        self.functions[name or callback.__name__] = callback

    def function(self, name: Optional[str] = None):
        """
        Register a function.
        :param name: Menu name.
        """

        def decorator(callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Awaitable[Any]]):
            self.register_function(callback=callback, name=name)
            return callback

        return decorator

    def mark_attached(self) -> bool:
        """
        Mark a router as attached.
        :return: True on success.
        """
        if self._was_attached:
            LOGGER.warning(f'You are trying to attach router named {self.name} more than once! *mad meowing*')
            return False
        self._was_attached = True
        return True

    def attach(self, neko: BaseNeko):
        """
        Attach a router to a Neko.
        :param neko: A Neko object.
        """
        if not self.mark_attached():
            return
        neko.functions.update(self.functions)
        neko.format_functions.update(self.format_functions)
        neko.prev_menu_handlers.update(self.prev_menu_handlers)
        neko.next_menu_handlers.update(self.next_menu_handlers)

    def register_prev_menu_handler(self, callback: Callable[[Menu], Awaitable[str]], name: Optional[str] = None):
        """
        Register a prev menu handler.
        :param callback: A prev menu handler to call.
        :param name: Menu name.
        """
        self.prev_menu_handlers[name or callback.__name__] = callback

    def prev_menu_handler(self, name: Optional[str] = None):
        """
        Register a prev menu handler.
        :param name: Menu name.
        """

        def decorator(callback: Callable[[Menu], Awaitable[str]]):
            self.register_prev_menu_handler(callback=callback, name=name)
            return callback

        return decorator

    def register_next_menu_handler(self, callback: Callable[[Menu], Awaitable[str]], name: Optional[str] = None):
        """
        Register a next menu handler.
        :param callback: A next menu handler to call.
        :param name: Menu name.
        """
        self.prev_menu_handlers[name or callback.__name__] = callback

    def next_menu_handler(self, name: Optional[str] = None):
        """
        Register a next menu handler.
        :param name: Menu name.
        """

        def decorator(callback: Callable[[Menu], Awaitable[str]]):
            self.register_next_menu_handler(callback=callback, name=name)
            return callback

        return decorator
