from __future__ import annotations

from .handlers import menu_callback_query_handler, menu_message_handler, default_start_function
from typing import Dict, List, Any, Callable, Union, Optional, TextIO, Awaitable
from aiogram.dispatcher.filters.builtin import ChatTypeFilter
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram import Dispatcher, Bot, executor, types
from .text_processors import add_json_texts
from .build_response import BuildResponse
from .filters import StartsWith, HasMenu
from .type_filters import _filters_to_dict
from datetime import datetime, timedelta
from .storages import BaseStorage
from copy import deepcopy
from asyncio import sleep
import logging

try:
    import ujson as json
except ImportError:
    import json


class Neko:
    def __init__(self, storage: BaseStorage = BaseStorage(), token: Optional[str] = None, bot: Optional[Bot] = None,
                 dp: Optional[Dispatcher] = None, only_messages_in_functions: bool = False,
                 start_function: Optional[Callable[[Union[types.Message, types.CallbackQuery], Neko], Any]] = None,
                 validate_text_names: bool = True):
        """
        Initialize a dispatcher
        :param token: Telegram bot token
        :param bot: Aiogram Bot object
        :param dp: Aiogram Dispatcher object
        :param storage: A class that inherits from BaseDatabase class
        :param only_messages_in_functions: Set true if you want text function to receive messages explicitly in the
        second parameter
        :param start_function: A custom start function
        :param validate_text_names: Set False if you want to skip text field validation
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

        if type(storage) == BaseStorage:  # Check if BaseStorage is used
            logging.warning('You are using BaseStorage which does not save data permanently and is only for tests!')
        self.texts: Dict[str, Dict[str, Any]] = dict()

        self.functions: Dict[str, Callable[[BuildResponse, Union[types.Message, types.CallbackQuery], Neko],
                                           Any]] = dict()
        self.only_messages_in_functions: bool = only_messages_in_functions
        self.format_functions: Dict[str, Callable[[BuildResponse, types.User, Neko], Any]] = dict()
        self._required_text_names: List[str] = ['start', 'wrong_content_type']
        self._validate_text_names: bool = validate_text_names
        self.start_function: Callable[[Union[types.Message, types.CallbackQuery]],
                                      Any] = start_function or default_start_function
        self.dp.middleware.setup(self.HandlerValidator(self))  # Setup the handler validator middleware

        self._cached_user_languages: Dict[str, Dict[str, Union[str, datetime]]] = dict()
        self._message_content_filters: Dict[str, Callable[[Union[types.Message, types.CallbackQuery]],
                                                          Awaitable[bool]]] = _filters_to_dict()
        self.register_handlers()

    class HandlerValidator(BaseMiddleware):
        """
        Neko injector middleware
        """

        def __init__(self, neko):
            self.neko: Neko = neko
            super(Neko.HandlerValidator, self).__init__()

        async def on_process_message(self, message: types.Message, _: dict):
            """
            This handler is called when dispatcher receives a message
            """
            # Get current handler
            message.conf['neko'] = self.neko

        async def on_process_callback_query(self, call: types.CallbackQuery, _: dict):
            """
            This handler is called when dispatcher receives a call
            """
            # Get current handler
            call.conf['neko'] = self.neko
            call.message.conf['neko'] = self.neko
            call.message.from_user = call.from_user

    def add_content_filter(self, callback: Callable[[Union[types.Message, types.CallbackQuery]], Awaitable[bool]],
                           name: Optional[str] = None):
        if name is None:
            name = callback.__name__
        self._message_content_filters[name or callback.__name__] = callback

    async def get_content_filter(self, name: str) -> Callable[[Union[types.Message, types.CallbackQuery]],
                                                              Awaitable[bool]]:
        callback = self._message_content_filters.get(name)
        if not callback:
            raise RuntimeError(f'Content filter {name} or type does not exist!')
        return callback

    def register_handlers(self):
        """
        Registers default handlers
        """
        self.dp.register_message_handler(self.start_function, ChatTypeFilter(types.ChatType.PRIVATE),
                                         commands=['start'])
        self.dp.register_callback_query_handler(menu_callback_query_handler, StartsWith('menu_'))
        self.dp.register_message_handler(menu_message_handler, ChatTypeFilter(types.ChatType.PRIVATE),
                                         HasMenu(self.storage), content_types=types.ContentType.ANY)

    def add_texts(self, texts: Union[Dict[str, Any], TextIO, str] = 'translations',
                  lang: Optional[str] = None, processor: str = 'json'):
        """
        Assigns a required piece of texts to use later
        :param texts: Dictionary or JSON containing texts, path to a file or path to a directory containing texts
        :param lang: Language of the texts
        :param processor: A text processor to use, currently only JSON is supported
        """
        if processor.lower() == 'json':
            for language, text in add_json_texts(required_texts=self._required_text_names, texts=texts, lang=lang,
                                                 validate_text_names=self._validate_text_names).items():
                if language in self.texts.keys():
                    self.texts[language].update(text)
                else:
                    logging.warning(f'Loaded {language} translation')
                    self.texts[language] = text
        else:
            raise ValueError('Wrong text processor name!')

    async def get_cached_user_language(self, user_id: Union[int, str]) -> Optional[str]:
        user_id = str(user_id)
        if (user_id in self._cached_user_languages.keys() and
                self._cached_user_languages[user_id]['date'] + timedelta(minutes=20) > datetime.now()):
            return self._cached_user_languages[user_id]['lang']
        else:
            return None

    async def cache_user_language(self, user_id: Union[str, int], lang: str):
        self._cached_user_languages[user_id] = {'date': datetime.now(), 'lang': lang}

    async def build_text(self, text: str, user: types.User, no_formatting: bool = False,
                         formatter_extras: Optional[Dict[str, Any]] = None,
                         text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                         lang: Optional[str] = None) -> BuildResponse:
        """
        Builds and returns the required text
        :param text: Text name
        :param user: Aiogram user object or its ID
        :param no_formatting: Whether to call a formatter
        :param formatter_extras: Extras to pass into a formatter
        :param text_format: Text format
        :param lang: Language to use
        :return: A BuildResponse object containing all the specified menu fields
        """
        if lang is None:
            lang = await self.get_cached_user_language(user_id=user.id)
            if lang is None:
                lang: str = await self.storage.get_user_language(user.id)
                await self.cache_user_language(user_id=user.id, lang=lang)

        data: Dict[str, Any] = deepcopy(self.texts.get(lang).get(text))
        extras: Dict[str, Any] = data.get('extras', dict())

        if formatter_extras:
            extras.update(formatter_extras)

        data['extras'] = extras
        data['name'] = text

        response: BuildResponse = BuildResponse(**data)

        if text_format:
            no_formatting = True
            if isinstance(text_format, list):
                response.data.text = response.data.text.format(*text_format)
            elif isinstance(text_format, dict):
                response.data.text = response.data.text.format(**text_format)
            else:
                response.data.text = response.data.text.format(text_format)

        if self.format_functions.get(text) and not no_formatting:
            function_return = await self.format_functions.get(text)(response, user, self)
            if isinstance(function_return, BuildResponse):  # If BuildResponse should be replaced
                response = function_return

        if response.data.markup is None and response.data.raw_markup:
            await response.data.assemble_markup()

        return response

    async def check_text_exists(self, text: str, lang: Optional[str] = None) -> bool:
        if lang is None:
            lang = list(self.texts.keys())[0]
        return text in self.texts[lang].keys()

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

    def register_function(self, callback: Callable[[BuildResponse,
                                                    Union[types.Message, types.CallbackQuery], Neko], Any],
                          name: Optional[str] = None):
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

    def start_polling(self, on_startup: Optional[callable] = None, on_shutdown: Optional[callable] = None):
        executor.start_polling(self.dp, on_startup=on_startup, on_shutdown=on_shutdown)

    async def delete_markup(self, user_id: int):
        """
        Remove reply markup for a user
        :param user_id: Telegram ID/Username of a target user/chat
        """
        keyboard = types.ReplyKeyboardMarkup([[types.KeyboardButton(text='❌')]], resize_keyboard=True)
        message = await self.bot.send_message(chat_id=user_id, text='❌', reply_markup=keyboard)
        await sleep(0.2)
        await message.delete()

    async def set_user_language(self, user_id: int, language: str):
        await self.storage.set_user_language(user_id=user_id, language=language)
        self._cached_user_languages.pop(str(user_id), None)
