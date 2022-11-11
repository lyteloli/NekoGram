from aiogram.dispatcher.filters.builtin import ChatTypeFilter
from .text_processors import BaseProcessor, JSONProcessor
from .filters import StartsWith, HasMenu, BuiltInFilters
from aiogram import Bot, Dispatcher, executor, types
from .storages import BaseStorage, MemoryStorage
from typing import Optional, Dict, List, Union
from aiogram.dispatcher.filters import Filter
from abc import ABC, abstractmethod
from .logger import LOGGER
from . import handlers


class BaseNeko(ABC):
    def __init__(self, storage: Optional[BaseStorage] = None, token: Optional[str] = None, bot: Optional[Bot] = None,
                 dp: Optional[Dispatcher] = None, text_processor: Optional[BaseProcessor] = None,
                 entrypoint: str = 'start', menu_prefixes: Union[List[str]] = 'menu_',
                 callback_parameters_delimiter: str = '#'):
        """
        Initialize a Neko
        :param storage: A class that inherits from BaseDatabase class
        :param token: Telegram bot token
        :param bot: Aiogram Bot object
        :param dp: Aiogram Dispatcher object
        :param text_processor: A text processor to use (a class inherited from text_processors.BaseProcessor),
        JSONProcessor by default
        :param entrypoint: App entrypoint menu name (defaults to start)
        :param menu_prefixes: Common prefixes for menus defined in translation files
        :param callback_parameters_delimiter: A delimiter for callback data arguments
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

        if storage is None:
            storage = MemoryStorage()
        self.storage: BaseStorage = storage

        if text_processor is None:
            text_processor = JSONProcessor()
        self.text_processor: BaseProcessor = text_processor

        if type(storage) == MemoryStorage:  # Check if MemoryStorage is used
            LOGGER.warning('You are using MemoryStorage which does not store data permanently! *sigh of condemnation*')

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

        print(r'''
   _  __    __        _____             
  / |/ /__ / /_____  / ___/______ ___ _ 
 /    / -_)  '_/ _ \/ (_ / __/ _ `/  ' \
/_/|_/\__/_/\_\\___/\___/_/  \_,_/_/_/_/''')

    def register_handlers(self):
        """
        Registers default handlers
        """
        self.dp.register_message_handler(handlers.menu_message_handler, ChatTypeFilter(types.ChatType.PRIVATE),
                                         commands=['start'])
        for menu_prefix in self.menu_prefixes:
            self.dp.register_callback_query_handler(handlers.menu_callback_query_handler, StartsWith(menu_prefix))
        if 'widget_' not in self.menu_prefixes:
            self.dp.register_callback_query_handler(handlers.menu_callback_query_handler, StartsWith('widget_'))
        self.dp.register_message_handler(handlers.menu_message_handler, ChatTypeFilter(types.ChatType.PRIVATE),
                                         HasMenu(self.storage), content_types=types.ContentType.ANY)

    def add_filter(self, name: str, callback: Union[callable, Filter]):
        if self.filters.get(name):
            LOGGER.warning(f'Filter named {name} was overridden. *eyes filling with tears*')

        if isinstance(callback, Filter):
            callback = callback.check
        self.filters[name] = callback

    def remove_filter(self, name: str):
        self.filters.pop(name)

    @abstractmethod
    async def check_text_exists(self, text: str, lang: Optional[str] = None) -> bool:
        pass

    def start_polling(self, on_startup: Optional[callable] = None, on_shutdown: Optional[callable] = None):
        executor.start_polling(self.dp, on_startup=on_startup, on_shutdown=on_shutdown)

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
    async def build_menu(self, name: str, obj: Union[types.Message, types.CallbackQuery]):
        pass
