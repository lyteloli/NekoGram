from __future__ import annotations

from .handlers import menu_callback_query_handler, menu_message_handler, default_start_function
from typing import Dict, List, Any, Callable, Union, Optional, TextIO
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram import Dispatcher, Bot, executor, types
from .filters import StartsWith, HasMenu
from .storages import BaseStorage
from os.path import isdir, isfile
from io import TextIOWrapper
from copy import deepcopy
from asyncio import sleep
from os import listdir
import logging

try:
    import ujson as json
except ImportError:
    import json


class Neko:
    def __init__(self, dp: Dispatcher, storage: BaseStorage, only_messages_in_functions: bool = False,
                 start_function: Optional[Callable[[Union[types.Message, types.CallbackQuery], Neko], Any]] = None,
                 validate_text_names: bool = True):
        """
        Initialize a dispatcher
        :param dp: Aiogram dispatcher object
        :param storage: A class that inherits from BaseDatabase class
        :param only_messages_in_functions: Set true if you want text function to receive messages explicitly in the
        second parameter
        :param start_function: A custom start function
        :param validate_text_names: Set False if you want to skip text field validation
        """
        self.bot: Bot = dp.bot
        self.dp: Dispatcher = dp
        self.storage: BaseStorage = storage
        if type(storage) == BaseStorage:
            logging.warning('You are using BaseStorage which doesn\'t save data permanently and is only for tests!')
        self.texts: Dict[str, Dict[str, Any]] = dict()
        self.functions: Dict[str, Callable[[Neko.BuildResponse, Union[types.Message, types.CallbackQuery], Neko],
                                           Any]] = dict()
        self.only_messages_in_functions: bool = only_messages_in_functions
        self._format_functions: Dict[str, Callable[[Neko.BuildResponse, types.User, Neko], Any]] = dict()
        self._required_text_names: List[str] = ['start', 'wrong_content_type']
        self._validate_text_names: bool = validate_text_names
        self.start_function: Callable[[Union[types.Message, types.CallbackQuery]],
                                      Any] = start_function or default_start_function
        self.dp.middleware.setup(self.HandlerValidator(self))  # Setup the handler validator middleware
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

    def register_handlers(self):
        """
        Registers default handlers
        """
        # self.dp.register_errors_handler(self.aiogram_error_handler, exception=aiogram_exc.TelegramAPIError)
        # self.dp.register_errors_handler(self.runtime_error_handler, exception=Exception)
        self.dp.register_message_handler(self.start_function, types.ChatType.is_private, commands=['start'])
        self.dp.register_callback_query_handler(menu_callback_query_handler, StartsWith('menu_'))
        self.dp.register_message_handler(menu_message_handler, types.ChatType.is_private, HasMenu(self.storage),
                                         content_types=types.ContentType.ANY)

    def add_texts(self, texts: Union[Dict[str, Any], TextIO, str] = 'translations', lang: Optional[str] = None):
        """
        Assigns a required piece of texts to use later
        :param texts: Dictionary or JSON containing texts, path to a file or path to a directory containing texts
        :param lang: Language of the texts
        """
        if not lang and isinstance(texts, str) and isdir(texts):  # Path to directory containing translations
            text_list = listdir(texts)
            for file in text_list:
                if file.endswith('.json'):
                    self.add_texts(texts=f'{texts}/{file}', lang=file.replace('.json', '').split('_')[0])
            return
        elif isinstance(texts, str) and not isfile(texts):  # String JSON
            texts = json.loads(texts)
        elif isinstance(texts, str) and isfile(texts):  # File path
            with open(texts, 'r') as file:
                texts = json.load(file)
        elif isinstance(texts, TextIOWrapper):  # IO JSON file
            texts = json.load(texts)
        else:
            raise ValueError('No valid text path or text supplied')

        if self._validate_text_names and isinstance(texts, dict) \
                and not all(elem in texts.keys() for elem in self._required_text_names):
            raise ValueError(f'The supplied translation for {lang} does not contain some of the required texts: '
                             f'{self._required_text_names}')

        if lang in self.texts.keys():
            self.texts[lang].update(texts)
        else:
            logging.warning(f'Loaded {lang} translation')
            self.texts[lang] = texts

    class BuildResponse:

        class Data:
            def __init__(self, name: str,
                         markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup,
                                                Dict[str, Any]]] = None,
                         text: Optional[str] = None, no_preview: Optional[bool] = None, silent: Optional[bool] = None,
                         markup_row_width: Optional[int] = None, parse_mode: Optional[str] = None,
                         allowed_items: Optional[List[str]] = None, extras: Optional[Dict[str, Any]] = None):
                self.name: str = name
                self.text: Optional[str] = text
                self.no_preview: Optional[bool] = no_preview
                self.parse_mode: Optional[str] = parse_mode
                self.silent: Optional[bool] = silent
                self.markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None
                self.markup_row_width: int = markup_row_width or 3
                self.raw_markup: Optional[List[Union[List[str], Dict[str, str]]]] = markup
                self.extras: Dict[str, Any] = extras or dict()
                self.allowed_items: Optional[List[str]] = allowed_items

            async def assemble_markup(self, text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                                      markup_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                                      markup: Optional[Union[types.InlineKeyboardMarkup,
                                                             types.ReplyKeyboardMarkup]] = None) -> \
                    Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]]:
                """
                Assembles markup
                """

                if isinstance(text_format, list):
                    self.text = self.text.format(*text_format)
                elif isinstance(text_format, dict):
                    self.text = self.text.format(**text_format)
                elif text_format is not None:
                    self.text = self.text.format(text_format)

                if self.raw_markup:

                    for row in self.raw_markup:
                        row_buttons: List[Union[types.InlineKeyboardButton, types.KeyboardButton]] = []

                        if isinstance(row, dict) and markup is None:
                            markup = types.InlineKeyboardMarkup(row_width=self.markup_row_width)
                        elif markup is None:
                            markup = types.ReplyKeyboardMarkup(row_width=self.markup_row_width, resize_keyboard=True)

                        if isinstance(markup, types.InlineKeyboardMarkup):
                            for key, value in row.items():

                                if isinstance(markup_format, list):
                                    key = key.format(*markup_format)
                                    value = value.format(*markup_format)
                                elif isinstance(markup_format, dict):
                                    key = key.format(**markup_format)
                                    value = value.format(**markup_format)
                                elif markup_format is not None:
                                    key = key.format(markup_format)
                                    value = value.format(markup_format)

                                if key.startswith(('http://', 'https://', 'tg://', 'url.')):
                                    if key.startswith('url.'):  # Remove the "url." prefix
                                        key = key[4:]
                                    row_buttons.append(types.InlineKeyboardButton(text=value, url=key))
                                else:
                                    row_buttons.append(types.InlineKeyboardButton(text=value, callback_data=key))
                        else:
                            for button in row:
                                row_buttons.append(types.KeyboardButton(text=button))
                        markup.add(*row_buttons)

                self.markup = markup
                return markup

            async def add_pagination(self, offset: int, found: int, limit: int):
                if offset >= limit and found > limit:
                    # Add previous and next buttons
                    self.raw_markup.append({f'{self.name}#{offset - limit}': '⬅️',
                                            f'{self.name}#{offset + limit}': '➡️'})
                elif offset >= limit:
                    self.raw_markup.append({f'{self.name}#{offset - limit}': '⬅️'})
                elif found > limit:
                    self.raw_markup.append({f'{self.name}#{offset + limit}': '➡️'})

        def __init__(self, **kwargs):
            self.function: Optional[Callable[[Neko.BuildResponse, Union[types.Message, types.CallbackQuery], Neko],
                                             Any]] = kwargs.get('function')
            self.back_menu: Optional[str] = kwargs.get('back_menu')
            kwargs.pop('back_menu', None)
            kwargs.pop('function', None)
            self.data = self.Data(**kwargs)

        async def answer_menu_call(self, answer: bool = True, answer_only: bool = False):
            self.data.extras['answer_call']: bool = answer
            self.data.extras['answer_only']: bool = answer_only

    async def build_text(self, text: str, user: Union[types.User, int], no_formatting: bool = False,
                         formatter_extras: Optional[Dict[str, Any]] = None,
                         text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None) -> BuildResponse:
        """
        Builds and returns the required text
        :param text_format: Text format
        :param text: Text name
        :param user: Aiogram user object or its ID
        :param no_formatting: Whether to call a formatter
        :param formatter_extras: Extras to pass into a formatter
        :return:
        """
        if not isinstance(user, types.User):  # Instantiate a user if needed
            user = types.User(id=user)

        lang: str = await self.storage.get_user_language(user.id)

        data: Dict[str, Any] = deepcopy(self.texts.get(lang).get(text))
        extras: Dict[str, Any] = dict()

        if formatter_extras:
            extras.update(formatter_extras)

        data['extras'] = extras
        data['name'] = text

        response: Neko.BuildResponse = self.BuildResponse(**data)

        if text_format:
            no_formatting = True
            if isinstance(text_format, list):
                response.data.text = response.data.text.format(*text_format)
            elif isinstance(text_format, dict):
                response.data.text = response.data.text.format(**text_format)
            else:
                response.data.text = response.data.text.format(text_format)

        if self._format_functions.get(text) and not no_formatting:
            function_return = await self._format_functions.get(text)(response, user, self)
            if isinstance(function_return, Neko.BuildResponse):  # If BuildResponse should be replaced
                response = function_return

        if response.data.markup is None and response.data.raw_markup:
            await response.data.assemble_markup()

        return response

    async def check_text_exists(self, text: str) -> bool:
        return text in self.texts[list(self.texts.keys())[0]].keys()

    def register_formatter(self, callback: Callable[[Neko.BuildResponse, types.User, Neko], Any],
                           name: Optional[str] = None):
        self._format_functions[name or callback.__name__] = callback

    def formatter(self, name: Optional[str] = None):
        """
        Register a formatter
        :param name: Formatter name
        """

        def decorator(callback: Callable[[Neko.BuildResponse, types.User, Neko], Any]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(self, callback: Callable[[Neko.BuildResponse,
                                                    Union[types.Message, types.CallbackQuery], Neko], Any],
                          name: Optional[str] = None):
        self.functions[name or callback.__name__] = callback

    def function(self, name: Optional[str] = None):
        """
        Register a function
        :param name: Function name
        """

        def decorator(callback: Callable[[Neko.BuildResponse, Union[types.Message, types.CallbackQuery], Neko], Any]):
            self.register_function(callback=callback, name=name)
            return callback

        return decorator

    def start_polling(self):
        executor.start_polling(self.dp)

    async def delete_markup(self, user_id: int):
        keyboard = types.ReplyKeyboardMarkup([[types.KeyboardButton(text='❌')]], resize_keyboard=True)
        message = await self.bot.send_message(chat_id=user_id, text='❌', reply_markup=keyboard)
        await sleep(0.2)
        await message.delete()
