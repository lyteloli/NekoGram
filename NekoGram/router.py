from typing import Callable, Optional, Union, Dict, Any, Awaitable
from .base_neko import BaseNeko
from aiogram import types
from .menus import Menu


class NekoRouter:
    def __init__(self, name: Optional[str] = None):
        self.functions: Dict[str, Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko],
                                           Awaitable[Any]]] = dict()
        self.format_functions: Dict[str, Callable[[Menu, types.User, BaseNeko], Awaitable[Any]]] = dict()
        self.prev_menu_handlers: Dict[str, Callable[[Menu], Awaitable[str]]] = dict()
        self.next_menu_handlers: Dict[str, Callable[[Menu], Awaitable[str]]] = dict()
        self.name = name
        self._was_attached: bool = False

    def register_formatter(self, callback: Callable[[Menu, types.User, BaseNeko], Awaitable[Any]],
                           name: Optional[str] = None):
        """
        Register a formatter
        :param callback: A formatter to call
        :param name: Menu name
        """
        self.format_functions[name or callback.__name__] = callback

    def formatter(self, name: Optional[str] = None):
        """
        Register a formatter
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu, types.User, BaseNeko], Awaitable[Any]]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(self, callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko],
                                                   Awaitable[Any]], name: Optional[str] = None):
        """
        Register a function
        :param callback: A function to call
        :param name: Menu name
        """
        self.functions[name or callback.__name__] = callback

    def function(self, name: Optional[str] = None):
        """
        Register a function
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Awaitable[Any]]):
            self.register_function(callback=callback, name=name)
            return callback

        return decorator

    def attach(self):
        if self._was_attached:
            raise RuntimeError('You are trying to attach the same router twice! *mad meowing*')
        self._was_attached = True

    def register_prev_menu_handler(self, callback: Callable[[Menu], Awaitable[str]], name: Optional[str] = None):
        """
        Register a prev menu handler
        :param callback: A prev menu handler to call
        :param name: Menu name
        """
        self.prev_menu_handlers[name or callback.__name__] = callback

    def prev_menu_handler(self, name: Optional[str] = None):
        """
        Register a prev menu handler
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu], Awaitable[str]]):
            self.register_prev_menu_handler(callback=callback, name=name)
            return callback

        return decorator

    def register_next_menu_handler(self, callback: Callable[[Menu], Awaitable[str]], name: Optional[str] = None):
        """
        Register a next menu handler
        :param callback: A next menu handler to call
        :param name: Menu name
        """
        self.prev_menu_handlers[name or callback.__name__] = callback

    def next_menu_handler(self, name: Optional[str] = None):
        """
        Register a next menu handler
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu], Awaitable[str]]):
            self.register_next_menu_handler(callback=callback, name=name)
            return callback

        return decorator
