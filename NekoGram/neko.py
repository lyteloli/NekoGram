from typing import Dict, List, Union, Optional, Any, Callable, Awaitable
from aiogram.dispatcher.filters import Filter
from aiogram import Dispatcher, Bot, types
from typing_extensions import deprecated  # noqa
from datetime import datetime
from copy import deepcopy
import inspect
import os

try:
    import ujson as json
except ImportError:
    import json

from .utils import HandlerInjector, NekoGramWarning
from .webhook import KittyWebhook, KittyExecutor
from .text_processors import BaseProcessor
from .storages import BaseStorage
from .base_neko import BaseNeko
from .router import NekoRouter
from .logger import LOGGER
from .menus import Menu


class Neko(BaseNeko):
    _registration_warned: bool = False
    _builtin_widgets: List[str] = ['broadcast', 'languages', 'stats', 'admins']
    _widgets_warned: bool = False
    __MENU_ARGS: List[str] = list(inspect.signature(Menu.__init__).parameters.keys())

    def __init__(
            self,
            storage: Optional[BaseStorage],
            token: Optional[str] = None,
            bot: Optional[Bot] = None,
            dp: Optional[Dispatcher] = None,
            text_processor: Optional[BaseProcessor] = None,
            menu_prefixes: Union[List[str]] = 'menu_',
            load_texts: bool = True,
            callback_parameters_delimiter: str = '#',
            attach_required_middleware: bool = True,
            webhook_host: str = 'localhost',
            webhook_port: Optional[int] = None,
            webhook_path: Optional[str] = None,
            webhook_url: Optional[str] = None
    ):
        super().__init__(
            storage=storage,
            token=token,
            bot=bot,
            dp=dp,
            text_processor=text_processor,
            menu_prefixes=menu_prefixes,
            callback_parameters_delimiter=callback_parameters_delimiter
        )
        if attach_required_middleware:
            self.dp.middleware.setup(HandlerInjector(self))  # Set up the handler injector middleware
        else:
            LOGGER.warning(
                'You canceled embedded middleware attachment, this is a dangerous thing to do, make sure '
                'you perform same actions in your middleware, otherwise the app will crash or become idle.'
            )

        self._cached_user_languages: Dict[str, Dict[str, Union[str, datetime]]] = dict()
        if load_texts:
            self.text_processor.add_texts()
        self.widgets: List[str] = list()
        self.__widget_data: Dict[str, Any] = dict()
        self.executor: KittyExecutor = KittyExecutor(neko=self)
        self.__webhook_host: str = webhook_host
        self.__webhook_port: Optional[int] = webhook_port
        self.__webhook_path: Optional[str] = webhook_path
        self.__webhook_url: Optional[str] = webhook_url
        if webhook_path and '{token}' not in webhook_path:
            raise ValueError('{token} placeholder has to be present in webhook_path.')

    def attach_filter(self, name: str, callback: Union[callable, Filter]):
        if self.filters.get(name):
            LOGGER.warning(f'Filter named {name} was overridden. *eyes filling with tears*')

        if isinstance(callback, Filter):
            callback = callback.check
        self.filters[name] = callback

    @deprecated(
        'The `add_filter` method is deprecated and may be removed in future updates, use `attach_filter` instead.',
        category=NekoGramWarning
    )
    def add_filter(self, name: str, callback: Union[callable, Filter]):
        self.attach_filter(name=name, callback=callback)

    def get_widget_data(self, key: str) -> Optional[Any]:
        return self.__widget_data.get(key)

    def get_full_widget_data(self) -> Dict[str, Any]:
        return self.__widget_data.copy()

    async def check_text_exists(self, text: str, lang: Optional[str] = None) -> bool:
        if lang is None:
            lang = list(self.text_processor.texts.keys())[0]
        return text in self.text_processor.texts[lang].keys()

    def register_formatter(
            self, callback: Callable[[Menu, types.User, BaseNeko], Awaitable[Any]], name: Optional[str] = None
    ):
        """
        Register a formatter.
        :param callback: A formatter to call.
        :param name: Menu name.
        """
        if not self._registration_warned:
            LOGGER.warning(
                'It is not recommended to register formatters and functions within a Neko class, '
                'consider using a NekoRouter.'
            )
            self._registration_warned = True
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
        if not self._registration_warned:
            LOGGER.warning(
                'It is not recommended to register formatters and functions within a Neko class, '
                'consider using a NekoRouter.'
            )
            self._registration_warned = True
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

    def register_markup_overrider(
            self,
            callback: Callable[[Menu], Awaitable[List[List[Dict[str, str]]]]],
            lang: str,
            name: Optional[str] = None
    ):
        """
        Register a markup overrider.
        :param callback: A markup overrider to call.
        :param lang: Language to override markup for.
        :param name: Menu name.
        """
        if name is None:
            name = callback.__name__
        if name not in self._markup_overriders:
            self._markup_overriders[name] = dict()
        self._markup_overriders[name][lang] = callback

    def markup_overrider(self, lang: str, name: Optional[str] = None):
        """
        Register a markup overrider.
        :param lang: Language to override markup for.
        :param name: Menu name.
        """

        def decorator(callback: Callable[[Menu], Awaitable[List[List[Dict[str, str]]]]]):
            self.register_markup_overrider(callback=callback, name=name, lang=lang)
            return callback

        return decorator

    async def build_menu(
            self,
            name: str,
            obj: Optional[Union[types.Message, types.CallbackQuery, types.InlineQuery]],
            user_id: Optional[int] = None,
            callback_data: Optional[Union[str, int]] = None,
            auto_build: bool = True, lang: Optional[str] = None
    ) -> Optional[Menu]:
        """
        Build a menu by its name.
        :param name: Menu name, same as in translation file.
        :param obj: An Aiogram Message or CallbackQuery object.
        :param user_id: An ID of a user to build menu for.
        :param callback_data: Callback data to assign to a menu.
        :param auto_build: Whether to build the Menu if no formatter is defined.
        :param lang: User language.
        :return: A Menu object.
        """
        if name == 'menu_start':  # Start patch
            name = 'start'

        if obj is None:
            obj = types.Message(**{'conf': {'neko': self}, 'from': types.User(id=user_id or 1)})

        if lang is None:
            lang = await self.storage.get_user_language(user_id=user_id or obj.from_user.id)
        text: Dict[str, Any] = deepcopy(self.text_processor.texts[lang].get(name))
        if text is None:  # Try to fetch the menu in another language
            text = self.text_processor.texts[self.storage.default_language].get(name)
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
        if text and text.get('text') is None and text.get('media') is None:
            LOGGER.warning(f'No text or media provided for {name}. *suspicious stare*')

        text.update(dict(name=name, obj=obj, callback_data=callback_data, bot_token=obj.conf.get('request_token')))
        menu = Menu(**text)

        if self._markup_overriders.get(name, dict()).get(lang):
            menu.raw_markup = await self._markup_overriders[name][lang](menu)

        format_func = self.format_functions.get(name)
        if format_func:
            r = await format_func(menu, obj.from_user, self)
            if isinstance(r, Menu):  # Replace the menu if required
                menu = r
            if menu.markup is None and menu.raw_markup:
                await menu.build()
        elif auto_build:
            await menu.build()

        return menu if not menu.is_broken else None

    def attach_router(self, router: NekoRouter):
        """
        Attach a NekoRouter to Neko.
        :param router: A NekoRouter to attach.
        """
        if not router.mark_attached():
            return
        self.functions.update(router.functions)
        self.format_functions.update(router.format_functions)
        self.prev_menu_handlers.update(router.prev_menu_handlers)
        self.next_menu_handlers.update(router.next_menu_handlers)

    async def attach_widget(
            self,
            formatters_router: NekoRouter,
            functions_router: NekoRouter,
            startup: Optional[Callable[[BaseNeko], Awaitable[Optional[Dict[str, Any]]]]] = None,
            texts_path: Optional[str] = None,
            db_table_structure_path: Optional[str] = None,
            formatters_to_ignore: Optional[List[str]] = None,
            functions_to_ignore: Optional[List[str]] = None
    ):
        """
        Attach a widget to Neko.
        :param formatters_router: A NekoRouter object responsible for formatters.
        :param functions_router: A NekoRouter object responsible for functions.
        :param startup: A startup function that returns data required for a widget to work to call.
        :param texts_path: A path to translation files.
        :param db_table_structure_path: A path to table structure file.
        :param formatters_to_ignore: A list of formatter names to ignore.
        :param functions_to_ignore: A list of function names to ignore.
        """
        if 'MySQLStorage' not in self.storage.__class__.__name__ and not self._widgets_warned:
            LOGGER.warning(f'Your storage is not MySQLStorage, widgets may function improperly.')
            self._widgets_warned = True
        if formatters_router.name is None or formatters_router.name != functions_router.name \
                or functions_router.name is None:
            raise RuntimeError('Widget router names must be present and must be same for formatter and function router')

        if formatters_router.name in self.widgets:
            LOGGER.warning(f'Widget {formatters_router.name} is being attached again, ignored. *ultrasonic meowing*')
            return

        if startup:
            raw_widget_data = await startup(self)
            if raw_widget_data:
                widget_data: Dict[str, Any] = dict()
                for key, value in raw_widget_data.items():
                    if not key.startswith(f'{formatters_router.name}_'):
                        LOGGER.warning(
                            f'Widget {formatters_router.name} is not allowed to access `{key}` in widget data, '
                            f'all keys for this widget have to start with `{formatters_router.name}_`. '
                            'This key was ignored. *visible disappointment*'
                        )
                    else:
                        widget_data[key] = value
                self.__widget_data.update(widget_data)
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

        if db_table_structure_path and self.storage.__class__.__name__ == 'MySQLStorage':
            with open(db_table_structure_path, 'r') as f:
                table_structure = json.load(f)
            await self.storage.add_tables(table_structure, required_by=formatters_router.name)

        if texts_path is None:
            if formatters_router.name in self._builtin_widgets:
                path = os.path.abspath(__file__).rstrip('neko.py')
                delim = path[-1]
                self.text_processor.add_texts(
                    f'{path}widgets{delim}{formatters_router.name}{delim}translations', is_widget=True
                )
            else:
                raise RuntimeError(
                    f'Widget {formatters_router.name} is not builtin, therefore texts_path has to be provided'
                )
        LOGGER.info(f'{formatters_router.name.capitalize()} widget attached successfully')

    def start_webhook(self, loop=None):
        """
        Start webhook.
        :param loop: Abstract asyncio loop.
        """
        if self.__webhook_path is None or self.__webhook_port is None:
            raise RuntimeError(
                'You must set webhook_host, webhook_host and webhook_port parameters for a Neko class '
                'during initialization to run a webhook'
            )
        self.executor.start_webhook(
            webhook_path=self.__webhook_path,
            host=self.__webhook_host,
            port=self.__webhook_port,
            request_handler=KittyWebhook,
            loop=loop
        )

    async def set_webhook(
            self, bot_token: str, validate_token: bool = True, drop_pending_updates: Optional[bool] = None
    ) -> types.User:
        """
        Set a webhook for a child bot.
        :param bot_token: Child bot token.
        :param validate_token: Whether to validate a token.
        :param drop_pending_updates: Whether to skip unprocessed updates for a child bot.
        """
        if self.__webhook_url is None or '{token}' not in self.__webhook_url:
            raise RuntimeError('webhook_url must be specified and contain {token} placeholder to set a webhook.')
        with self.bot.with_token(bot_token=bot_token, validate_token=validate_token):
            await self.bot.set_webhook(
                url=self.__webhook_url.format(token=bot_token), drop_pending_updates=drop_pending_updates
            )
            return await self.bot.get_me()
