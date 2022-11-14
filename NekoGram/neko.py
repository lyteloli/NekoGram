from typing import Dict, List, Union, Optional, Any, Callable, Awaitable
from .text_processors import BaseProcessor
from aiogram import Dispatcher, Bot, types
from .storages.mysql import MySQLStorage
from .utils import HandlerInjector
from .storages import BaseStorage
from .base_neko import BaseNeko
from .router import NekoRouter
from datetime import datetime
from .logger import LOGGER
from copy import deepcopy
from .menus import Menu

try:
    import ujson as json
except ImportError:
    import json


class Neko(BaseNeko):
    _registration_warned: bool = False
    _builtin_widgets: List[str] = ['broadcast', 'languages']
    _widgets_warned: bool = False

    def __init__(self, storage: Optional[BaseStorage] = None, token: Optional[str] = None, bot: Optional[Bot] = None,
                 dp: Optional[Dispatcher] = None, text_processor: Optional[BaseProcessor] = None,
                 menu_prefixes: Union[List[str]] = 'menu_', load_texts: bool = True,
                 callback_parameters_delimiter: str = '#'):
        super().__init__(storage=storage, token=token, bot=bot, dp=dp, text_processor=text_processor,
                         menu_prefixes=menu_prefixes, callback_parameters_delimiter=callback_parameters_delimiter)
        self.dp.middleware.setup(HandlerInjector(self))  # Set up the handler injector middleware

        self._cached_user_languages: Dict[str, Dict[str, Union[str, datetime]]] = dict()
        if load_texts:
            self.text_processor.add_texts()
        self.functions: Dict[str, Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko],
                                           Awaitable[Any]]] = dict()
        self.format_functions: Dict[str, Callable[[Menu, types.User, BaseNeko], Awaitable[Any]]] = dict()
        self.prev_menu_handlers: Dict[str, Callable[[Menu], Awaitable[str]]] = dict()
        self.next_menu_handlers: Dict[str, Callable[[Menu], Awaitable[str]]] = dict()
        self._markup_overriders: Dict[str, Dict[str, Callable[[Menu], Awaitable[List[List[Dict[str, str]]]]]]] = dict()
        self.widgets: List[str] = list()

    async def check_text_exists(self, text: str, lang: Optional[str] = None) -> bool:
        if lang is None:
            lang = list(self.text_processor.texts.keys())[0]
        return text in self.text_processor.texts[lang].keys()

    def register_formatter(self, callback: Callable[[Menu, types.User, BaseNeko], Any], name: Optional[str] = None):
        """
        Register a formatter
        :param callback: A formatter to call
        :param name: Menu name
        """
        if not self._registration_warned:
            LOGGER.warning('It is not recommended to register formatters within a Neko class, '
                           'consider using a NekoRouter')
            self._registration_warned = True
        self.format_functions[name or callback.__name__] = callback

    def formatter(self, name: Optional[str] = None):
        """
        Register a formatter
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu, types.User, BaseNeko], Any]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(self, callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Any],
                          name: Optional[str] = None):
        """
        Register a function
        :param callback: A function to call
        :param name: Menu name
        """
        if not self._registration_warned:
            LOGGER.warning('It is not recommended to register functions within a Neko class, '
                           'consider using a NekoRouter')
            self._registration_warned = True
        self.functions[name or callback.__name__] = callback

    def function(self, name: Optional[str] = None):
        """
        Register a function
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu, Union[types.Message, types.CallbackQuery], BaseNeko], Any]):
            self.register_function(callback=callback, name=name)
            return callback

        return decorator

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

    def register_markup_overrider(self, callback: Callable[[Menu], Awaitable[List[List[Dict[str, str]]]]], lang: str,
                                  name: Optional[str] = None):
        """
        Register a markup overrider
        :param callback: A markup overrider to call
        :param lang: Language to override markup for
        :param name: Menu name
        """
        if name is None:
            name = callback.__name__
        if name not in self._markup_overriders:
            self._markup_overriders[name] = dict()
        self._markup_overriders[name][lang] = callback

    def markup_overrider(self, lang: str, name: Optional[str] = None):
        """
        Register a markup overrider
        :param lang: Language to override markup for
        :param name: Menu name
        """

        def decorator(callback: Callable[[Menu], Awaitable[List[List[Dict[str, str]]]]]):
            self.register_markup_overrider(callback=callback, name=name, lang=lang)
            return callback

        return decorator

    async def build_menu(self, name: str, obj: Union[types.Message, types.CallbackQuery],
                         user_id: Optional[int] = None,
                         callback_data: Optional[Union[str, int]] = None,
                         auto_build: bool = True) -> Optional[Menu]:
        """
        Build a menu by its name
        :param name: Menu name, same as in translation file
        :param obj: An Aiogram Message or CallbackQuery object
        :param user_id: An ID of a user to build menu for
        :param callback_data: Callback data to assign to a menu
        :param auto_build: Whether to build the Menu if no formatter is defined
        :return: A Menu object
        """
        if name == 'menu_start':  # Start patch
            name = 'start'

        lang = await self.storage.get_user_language(user_id=user_id or obj.from_user.id)
        text = deepcopy(self.text_processor.texts[lang].get(name))
        if not obj:
            raise RuntimeError(f'Neither Message nor CallbackQuery was provided during menu building for {name}! '
                               f'*brain explosion sounds accompanied by intense meowing*')
        if text is None:  # Try to fetch the menu in another language
            if 'en' in self.text_processor.texts.keys():
                text = self.text_processor.texts['en'].get(name)
            if text is None:
                for language in self.text_processor.texts.keys():
                    text = self.text_processor.texts[language].get(name)
                    if text:
                        LOGGER.warning(f'{name} menu does not have {lang} translation, using {language}.')
                        break
            else:
                LOGGER.warning(f'{name} menu does not have {lang} translation, using en.')
            if text is None:
                raise RuntimeError(f'There is no menu called {name}! *facePAWm*')
        if text.get('text') is None and text:
            LOGGER.warning(f'No text provided for {name}. *suspicious stare*')
        menu = Menu(name=name, obj=obj, markup=text.get('markup'), markup_row_width=text.get('markup_row_width'),
                    text=text.get('text'), no_preview=text.get('no_preview'), parse_mode=text.get('parse_mode'),
                    silent=text.get('silent'), validation_error=text.get('validation_error'),
                    extras=text.get('extras'), keyboard_values_to_format=text.get('keyboard_values_to_format'),
                    markup_type=text.get('markup_type'), prev_menu=text.get('prev_menu'),
                    next_menu=text.get('next_menu'), filters=text.get('filters'), callback_data=callback_data)

        if self._markup_overriders.get(name, dict()).get(lang):
            menu.raw_markup = await self._markup_overriders[name][lang](menu)

        format_func = self.format_functions.get(name)
        if format_func:
            await format_func(menu, obj.from_user, self)
            if menu.markup is None and menu.raw_markup:
                await menu.build()
        elif auto_build:
            await menu.build()

        return menu if not menu.is_broken else None

    def attach_router(self, router: NekoRouter):
        """
        Attach a NekoRouter to Neko
        :param router: A NekoRouter to attach
        """
        router.attach()
        self.functions.update(router.functions)
        self.format_functions.update(router.format_functions)

    async def attach_widget(self, formatters_router: NekoRouter, functions_router: NekoRouter,
                            startup: Callable[[BaseNeko], Awaitable[Any]], texts_path: Optional[str] = None,
                            db_table_structure_path: Optional[str] = None,
                            formatters_to_ignore: Optional[List[str]] = None,
                            functions_to_ignore: Optional[List[str]] = None):
        """
        Attach a widget to Neko
        :param formatters_router: A NekoRouter object responsible for formatters
        :param functions_router: A NekoRouter object responsible for functions
        :param startup: A startup function to call
        :param texts_path: A path to translation files
        :param db_table_structure_path: A path to table structure file
        :param formatters_to_ignore: A list of formatter names to ignore
        :param functions_to_ignore: A list of function names to ignore
        """
        if not isinstance(self.storage, MySQLStorage) and not self._widgets_warned:
            LOGGER.warning(f'Your storage is not MySQLStorage, widgets may function improperly.')
            self._widgets_warned = True
        if formatters_router.name is None or formatters_router.name != functions_router.name \
                or functions_router.name is None:
            raise RuntimeError('Widget router names must be present and must be same for formatter and function router')

        if formatters_router.name in self.widgets:
            LOGGER.warning(f'Widget {formatters_router.name} is being attached again, ignored. *ultrasonic meowing*')
            return

        await startup(self)
        self.widgets.append(formatters_router.name)

        if formatters_to_ignore:  # Ignore formatters
            for name, func in formatters_router.format_functions.copy().items():
                if name in formatters_to_ignore:
                    formatters_router.format_functions.pop(name)

        if functions_to_ignore:  # Ignore functions
            for name, func in functions_router.functions.copy().items():
                if name in functions_to_ignore:
                    functions_router.functions.pop(name)

        self.attach_router(formatters_router)
        self.attach_router(functions_router)

        if texts_path is None:
            if formatters_router.name in self._builtin_widgets:
                texts_path = f'NekoGram/widgets/{formatters_router.name}/translations'
            else:
                raise RuntimeError(f'Widget {formatters_router.name} is not builtin, '
                                   f'therefore texts_path has to be provided')
        if db_table_structure_path and isinstance(self.storage, MySQLStorage):
            with open(db_table_structure_path, 'r') as f:
                table_structure = json.load(f)
            await self.storage.add_tables(table_structure, required_by=formatters_router.name)

        self.text_processor.add_texts(texts_path, is_widget=True)
        LOGGER.info(f'{formatters_router.name.capitalize()} widget attached successfully')
