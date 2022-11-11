from typing import Callable, Optional, Union, Dict, Any
from .base_neko import BaseNeko
from aiogram import types
from .menus import Menu


class NekoRouter:
    def __init__(self, name: Optional[str] = None):
        self.functions: Dict[str, Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Any]] = dict()
        self.format_functions: Dict[str, Callable[[Menu, types.User, BaseNeko], Any]] = dict()
        self.name = name
        self._was_attached: bool = False

    def register_formatter(self, callback: Callable[[Menu, types.User, BaseNeko], Any], name: Optional[str] = None):
        self.format_functions[name or callback.__name__] = callback

    def formatter(self, name: Optional[str] = None):
        """
        Register a formatter
        :param name: Formatter name
        """

        def decorator(callback: Callable[[Menu, types.User, BaseNeko], Any]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(self, callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Any],
                          name: Optional[str] = None):
        self.functions[name or callback.__name__] = callback

    def function(self, name: Optional[str] = None):
        """
        Register a function
        :param name: Function name
        """

        def decorator(callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Any]):
            self.register_function(callback=callback, name=name)
            return callback

        return decorator

    def attach(self):
        if self._was_attached:
            raise RuntimeError('You are trying to attach the same router twice! *mad meowing*')
        self._was_attached = True
