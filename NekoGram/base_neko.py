from typing import Optional, Dict, List, Union, Any, Callable, Awaitable
from aiogram.dispatcher.filters.builtin import ChatTypeFilter
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Filter
from abc import ABC, abstractmethod

from .text_processors import BaseProcessor, JSONProcessor
from .filters import StartsWith, HasMenu, BuiltInFilters
from .storages import BaseStorage
from . import handlers


class BaseNeko(ABC):
    def __init__(
            self,
            storage: Optional[BaseStorage],
            token: Optional[str] = None,
            bot: Optional[Bot] = None,
            dp: Optional[Dispatcher] = None,
            text_processor: Optional[BaseProcessor] = None,
            entrypoint: str = 'start',
            menu_prefixes: Union[List[str]] = 'menu_',
            callback_parameters_delimiter: str = '#',
            delete_messages: bool = True
    ):
        """
        Initialize a Neko.
        :param storage: A class that inherits from BaseDatabase class.
        :param token: Telegram bot token.
        :param bot: Aiogram Bot object.
        :param dp: Aiogram Dispatcher object.
        :param text_processor: A text processor to use (a class inherited from text_processors.BaseProcessor),
        JSONProcessor by default.
        :param entrypoint: App entrypoint menu name (defaults to start).
        :param menu_prefixes: Common prefixes for menus defined in translation files.
        :param callback_parameters_delimiter: A delimiter for callback data arguments.
        :param delete_messages: Whether to delete old messages in conversation automatically.
        """
        self.bot: Bot
        self.dp: Dispatcher
        if dp:
            self.bot, self.dp = (dp.bot, dp)
        elif bot:
            self.bot, self.dp = (bot, Dispatcher(bot=bot))
        elif token:
            self.bot = Bot(token=token)
            self.dp = Dispatcher(bot=self.bot)
        else:
            raise ValueError('No Dispatcher, Bot or token provided during Neko initialization')

        self.storage: BaseStorage = storage

        if text_processor is None:
            text_processor = JSONProcessor()
        self.text_processor: BaseProcessor = text_processor

        if isinstance(menu_prefixes, str):
            menu_prefixes = [menu_prefixes]
        self._entrypoint: str = entrypoint
        self.menu_prefixes: List[str] = menu_prefixes
        self.filters: Dict[str, callable] = dict()
        self.callback_parameters_delimiter: str = callback_parameters_delimiter
        self.register_handlers()

        builtin_filters = BuiltInFilters()
        for f in builtin_filters.to_list:
            self.filters[f] = getattr(builtin_filters, f'is_{f}')

        self.functions: Dict[str, Callable[
            [Any, Union[types.Message, types.CallbackQuery, types.InlineQuery], BaseNeko], Awaitable[Any]
        ]] = dict()
        self.format_functions: Dict[str, Callable[[Any, types.User, BaseNeko], Awaitable[Any]]] = dict()
        self.prev_menu_handlers: Dict[str, Callable[[Any], Awaitable[str]]] = dict()
        self.next_menu_handlers: Dict[str, Callable[[Any], Awaitable[str]]] = dict()
        self._markup_overriders: Dict[str, Dict[str, Callable[[Any], Awaitable[List[List[Dict[str, str]]]]]]] = dict()
        self.delete_messages: bool = delete_messages

        print(r'''
   _  __    __        _____             
  / |/ /__ / /_____  / ___/______ ___ _ 
 /    / -_)  '_/ _ \/ (_ / __/ _ `/  ' \
/_/|_/\__/_/\_\\___/\___/_/  \_,_/_/_/_/
''')

    def register_handlers(self):
        """
        Registers default handlers.
        """
        self.dp.register_message_handler(
            handlers._start_handler, ChatTypeFilter(types.ChatType.PRIVATE), commands=['start']  # noqa
        )
        for menu_prefix in self.menu_prefixes:
            self.dp.register_callback_query_handler(handlers.menu_callback_query_handler, StartsWith(menu_prefix))
        if 'widget_' not in self.menu_prefixes:
            self.dp.register_callback_query_handler(handlers.menu_callback_query_handler, StartsWith('widget_'))
        self.dp.register_message_handler(
            handlers.menu_message_handler,
            ChatTypeFilter(types.ChatType.PRIVATE),
            HasMenu(self.storage),
            content_types=types.ContentType.ANY
        )

    @abstractmethod
    def attach_filter(self, name: str, callback: Union[callable, Filter]):
        pass

    def remove_filter(self, name: str):
        self.filters.pop(name)

    @abstractmethod
    def get_widget_data(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def get_full_widget_data(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def check_text_exists(self, text: str, lang: Optional[str] = None) -> bool:
        pass

    def start_polling(
            self,
            *,
            on_startup: Optional[callable] = None,
            on_shutdown: Optional[callable] = None,
            loop: Any = None,
            skip_updates: bool = False,
            reset_webhook: bool = True,
            timeout: int = 20,
            relax: float = 0.1,
            fast: bool = True,
            allowed_updates: Optional[List[str]] = None
    ) -> None:
        executor.start_polling(
            self.dp,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            loop=loop,
            skip_updates=skip_updates,
            reset_webhook=reset_webhook,
            timeout=timeout,
            relax=relax,
            fast=fast,
            allowed_updates=allowed_updates
        )

    @abstractmethod
    def register_formatter(self, callback: callable, name: Optional[str] = None):
        pass

    @abstractmethod
    def formatter(self, name: Optional[str] = None):
        pass

    @abstractmethod
    def register_function(self, callback: callable, name: Optional[str] = None):
        pass

    @abstractmethod
    def function(self, name: Optional[str] = None):
        pass

    @abstractmethod
    def register_prev_menu_handler(self, callback: callable, name: Optional[str] = None):
        pass

    @abstractmethod
    def prev_menu_handler(self, name: Optional[str] = None):
        pass

    @abstractmethod
    def register_next_menu_handler(self, callback: callable, name: Optional[str] = None):
        pass

    @abstractmethod
    def next_menu_handler(self, name: Optional[str] = None):
        pass

    @abstractmethod
    def register_markup_overrider(self, callback: callable, lang: str, name: Optional[str] = None):
        pass

    @abstractmethod
    def markup_overrider(self, lang: str, name: Optional[str] = None):
        pass

    @abstractmethod
    async def build_menu(
            self,
            name: str,
            obj: Union[types.Message, types.CallbackQuery, types.InlineQuery],
            user_id: Optional[int] = None,
            callback_data: Optional[Union[str, int]] = None,
            auto_build: bool = True
    ):
        pass
