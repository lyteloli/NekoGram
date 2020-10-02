from typing import Dict, Callable, Any, Union, Optional
from aiogram import types
from .neko import Neko, BuildResponse


class NekoRouter:
    def __init__(self):
        self.functions: Dict[str, Callable[[BuildResponse, Union[types.Message, types.CallbackQuery],
                                            Neko], Any]] = dict()
        self.format_functions: Dict[str, Callable[[BuildResponse, types.User, Neko], Any]] = dict()

    def register_formatter(self, callback: Callable[[BuildResponse, types.User, Neko], Any],
                           name: Optional[str] = None):
        self.format_functions[name or callback.__name__] = callback

    def formatter(self, name: Optional[str] = None):
        """
        Register a formatter
        :param name: Formatter name
        """

        def decorator(callback: Callable[[BuildResponse, types.User, Neko], Any]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(self, callback: Callable[[BuildResponse, Union[types.Message, types.CallbackQuery],
                                                    Neko], Any], name: Optional[str] = None):
        self.functions[name or callback.__name__] = callback

    def function(self, name: Optional[str] = None):
        """
        Register a function
        :param name: Function name
        """

        def decorator(callback: Callable[[BuildResponse, Union[types.Message, types.CallbackQuery], Neko], Any]):
            self.register_function(callback=callback, name=name)
            return callback

        return decorator

    def attach_router(self, neko: Neko):
        """
        Attach a router to Neko
        :param neko: A Neko class
        """
        neko.format_functions.update(self.format_functions)
        neko.functions.update(self.functions)
