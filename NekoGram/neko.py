from __future__ import annotations

from aiogram import exceptions as aiogram_exceptions, Dispatcher, Bot, executor, types
from typing import Dict, List, Any, Callable, Union, Optional, TextIO
from aiogram.dispatcher.middlewares import BaseMiddleware
from .storages.base_storage import BaseStorage
from .filters import StartsWith, HasMenu
from os.path import isdir, isfile
from io import TextIOWrapper
from copy import deepcopy
from asyncio import sleep
from os import listdir

try:
    import ujson as json
except ImportError:
    import json


class Neko:
    def __init__(self, dp: Dispatcher, storage: BaseStorage, only_messages_in_functions: bool = False,
                 start_function: Optional[Callable[[Union[types.Message, types.CallbackQuery], Neko], Any]] = None):
        """
        Initialize a dispatcher
        :param dp: Aiogram dispatcher object
        :param storage: A class that inherits from BaseDatabase class
        :param only_messages_in_functions: Set true if you want text function to receive messages explicitly in the
        second parameter
        :param start_function: A custom start function
        """
        self.bot: Bot = dp.bot
        self.dp: Dispatcher = dp
        self.storage: BaseStorage = storage
        self.texts: Dict[str, Any] = dict()
        self._functions: Dict[str, Callable[[Neko.BuildResponse, Union[types.Message, types.CallbackQuery], Neko],
                                            Any]] = dict()
        self.only_messages_in_functions: bool = only_messages_in_functions
        self._format_functions: Dict[str, Callable[[Neko.BuildResponse, types.User, Neko], Any]] = dict()
        self._required_text_names: List[str] = ['start', 'wrong_content_type']
        self.start_function: Callable[[Union[types.Message, types.CallbackQuery]],
                                      Any] = start_function or self.default_start_function
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
        self.dp.register_callback_query_handler(self.menu_callback_query_handler, StartsWith('menu_'))
        self.dp.register_message_handler(self.menu_message_handler, types.ChatType.is_private, HasMenu(self.storage),
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
                    self.add_texts(texts=f'{texts}/{file}', lang=file.replace('.json', ''))
                    print(f'Loaded {file.replace(".json", "")} translation')
        elif isinstance(texts, str) and not isfile(texts):  # String JSON
            texts = json.loads(texts)
        elif isinstance(texts, str) and isfile(texts):  # File path
            with open(texts, 'r') as file:
                texts = json.load(file)
        elif isinstance(texts, TextIOWrapper):  # IO JSON file
            texts = json.load(texts)
        else:
            raise ValueError('No valid text path or text supplied')

        if isinstance(texts, dict) and not all(elem in texts.keys() for elem in self._required_text_names):
            raise ValueError(f'The supplied translation for {lang} does not contain some of the required texts: '
                             f'{self._required_text_names}')

        self.texts[lang] = texts

    class BuildResponse:

        class Data:
            def __init__(self, name: str,
                         markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup, Dict[str, Any]]],
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
                markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = markup

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
            self.data = self.Data(**kwargs)
            self.function: Optional[Callable[[Neko.BuildResponse, Union[types.Message, types.CallbackQuery], Neko],
                                             Any]] = kwargs.get('function')

        async def answer_menu_call(self, answer: bool = True, answer_only: bool = False):
            self.data.extras['answer_call']: bool = answer
            self.data.extras['answer_only']: bool = answer_only

    async def build_text(self, text: str, user: types.User, no_formatting: bool = False,
                         formatter_extras: Optional[Dict[str, Any]] = None,
                         text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None) -> BuildResponse:
        """
        Builds and returns the required text
        :param text_format: Text format
        :param text: Text name
        :param user: Aiogram user object
        :param no_formatting: Whether to call a formatter
        :param formatter_extras: Extras to pass into a formatter
        :return:
        """
        lang: str = await self.storage.get_user_language(user.id)

        if lang is None:
            raise ValueError(f'User {user.id} has no language. ({text})')

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

    def register_formatter(self, callback: Callable[[Neko.BuildResponse, types.User, Neko], Any], name: str):
        self._format_functions[name] = callback

    def formatter(self, name: str):
        """
        Register a formatter
        :param name: Formatter name
        """

        def decorator(callback: Callable[[Neko.BuildResponse, types.User, Neko], Any]):
            self.register_formatter(callback=callback, name=name)
            return callback

        return decorator

    def register_function(self, callback: Callable[[Neko.BuildResponse,
                                                    Union[types.Message, types.CallbackQuery], Neko], Any], name: str):
        self._functions[name] = callback

    def function(self, name: str):
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

    @staticmethod
    async def default_start_function(message: Union[types.Message, types.CallbackQuery]):
        neko: Neko = message.conf['neko']
        if not await neko.storage.check_user_exists(user_id=message.from_user.id):
            lang = message.from_user.language_code if message.from_user.language_code in neko.texts.keys() else 'en'
            await neko.storage.create_user(user_id=message.from_user.id, language=lang)
            await sleep(0.1)  # Sleep a bit to make sure user is added to the database
        else:
            # Completely erase user data
            await neko.storage.set_user_data(user_id=message.from_user.id, data={}, replace=True)

        data = await neko.build_text(text='start', user=message.from_user)
        if isinstance(message, types.Message):
            await message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                                disable_web_page_preview=data.data.no_preview, reply=False,
                                disable_notification=data.data.silent, reply_markup=data.data.markup)
            await message.delete()
        else:
            await message.message.edit_text(text=data.data.text, disable_web_page_preview=data.data.no_preview,
                                            reply_markup=data.data.markup, parse_mode=data.data.parse_mode)

    @staticmethod
    async def menu_callback_query_handler(call: types.CallbackQuery):
        neko: Neko = call.conf['neko']
        call_data: Optional[int] = None
        new_call_data: str = call.data

        if '#' in call.data:  # If data is supplied
            call_data: str = call.data.split('#')[1]  # Just the data
            call_data = int(call_data) if call_data.isnumeric() else call_data  # Make data an int if it is numeric
            new_call_data = call.data.split('#')[0]  # Real call

        if new_call_data == 'menu_start':
            await neko.start_function(call)  # Start function should completely erase all user data
            return

        if '_step_' not in new_call_data and not await neko.check_text_exists(new_call_data):
            new_call_data += '_step_1'  # Add a step_1 to the name if such text doesn't exist

        data = await neko.build_text(text=new_call_data, user=call.from_user, formatter_extras={'call_data': call_data})

        # If the current menu has a function, call it
        if data.function or (neko._functions.get(new_call_data) and not data.data.allowed_items):
            call_or_message = call.message if neko.only_messages_in_functions else call
            if await neko._functions[new_call_data](data, call_or_message, neko) is True:
                await neko.start_function(call)  # Start function should completely erase all user data
                await call.answer()
            return

        if data.data.extras.get('answer_call', False):  # If the call should be answered
            await call.answer(text=data.data.text, show_alert=True)
            if data.data.extras.get('answer_only', False):  # If only the call answer is required
                return

        await call.answer()

        if isinstance(data.data.markup, types.InlineKeyboardMarkup) or data.data.markup is None:
            await call.message.edit_text(text=data.data.text, parse_mode=data.data.parse_mode,
                                         disable_web_page_preview=data.data.no_preview, reply_markup=data.data.markup)
        else:
            await neko.storage.set_user_data(user_id=call.from_user.id, data={'menu': new_call_data})
            try:
                await call.message.delete()
            except aiogram_exceptions.MessageCantBeDeleted:
                await call.message.edit_reply_markup()
            await call.message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                                     disable_web_page_preview=data.data.no_preview, reply=False,
                                     disable_notification=data.data.silent, reply_markup=data.data.markup)

    @staticmethod
    async def menu_message_handler(message: types.Message):
        neko: Neko = message.conf['neko']
        user_data: Union[Dict[str, Any], bool] = await neko.storage.get_user_data(user_id=message.from_user.id)
        current_menu_name: str = user_data.get('menu')
        current_menu = await neko.build_text(text=current_menu_name, user=message.from_user)
        current_menu_step: int = int(current_menu_name.split('_step_')[1]) if '_step_' in current_menu_name else 0
        next_menu_name: str = current_menu_name.split('_step_')[0] + '_step_' + str(current_menu_step + 1)

        if message.text.startswith('⬅️'):  # If BACK button was clicked
            await neko.delete_markup(user_id=message.from_user.id)
            user_data.pop(current_menu_name, None)  # Delete items gathered by the current menu
            if current_menu_step > 1:  # Menu steps start from 1
                prev_menu_name = current_menu_name.split('_step_')[0] + '_step_' + str(current_menu_step - 1)
                data = await neko.build_text(text=prev_menu_name, user=message.from_user)
                user_data['menu'] = prev_menu_name
                await neko.storage.set_user_data(data=user_data, user_id=message.from_user.id, replace=True)
                await message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                                    disable_web_page_preview=data.data.no_preview, reply=False,
                                    disable_notification=data.data.silent, reply_markup=data.data.markup)
            else:
                await neko.start_function(message)  # Start function should completely erase all user data
            return

        if current_menu.data.allowed_items:  # If any item is required to proceed to the next menu step
            if message.content_type not in current_menu.data.allowed_items \
                    and current_menu.data.allowed_items[0] != 'any':
                data = await neko.build_text(text='wrong_content_type', user=message.from_user)
                await message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                                    disable_web_page_preview=data.data.no_preview, reply=False,
                                    disable_notification=data.data.silent, reply_markup=data.data.markup)
                return

            # Update user data
            if isinstance(message[message.content_type], list):
                result = message[message.content_type][-1].as_json()
            elif isinstance(message[message.content_type], str):
                result = message[message.content_type]
            else:
                result = message[message.content_type].as_json()
            user_data[current_menu_name] = result
        user_data['menu'] = next_menu_name
        await neko.storage.set_user_data(data=user_data, user_id=message.from_user.id, replace=True)

        if neko._functions.get(current_menu_name):  # If the current menu has a function, call it
            await neko.delete_markup(user_id=message.from_user.id)
            if await neko._functions[current_menu_name](current_menu, message, neko) is True:
                await neko.start_function(message)  # Start function should completely erase all user data
            return

        if not await neko.check_text_exists(next_menu_name):  # Check if text exists, use start if not
            await neko.start_function(message)  # Start function should completely erase all user data
            return

        next_menu = await neko.build_text(text=next_menu_name, user=message.from_user)

        await message.reply(text=next_menu.data.text, parse_mode=next_menu.data.parse_mode,
                            disable_web_page_preview=next_menu.data.no_preview, reply=False,
                            disable_notification=next_menu.data.silent, reply_markup=next_menu.data.markup)
