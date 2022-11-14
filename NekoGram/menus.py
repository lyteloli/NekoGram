from typing import Optional, Union, Dict, List, Any, Type
from contextlib import suppress
from .base_neko import BaseNeko
from aiogram import types
from .logger import LOGGER


class Menu:
    _default_keyboard_values: Dict[str, str] = {'callback_data': 'call_data', 'switch_inline_query': 'query',
                                                'switch_inline_query_current_chat': 'cc_query',
                                                'text': 'text', 'url': 'url'}
    _inline_markup_identifiers: List[str] = ['call_data', 'callback_data', 'query', 'switch_inline_query', 'cc_query',
                                             'switch_inline_query_current_chat', 'url']

    def __init__(self, name: str, obj: Union[types.Message, types.InlineQuery],
                 markup: Optional[List[List[Dict[str, str]]]] = None, markup_row_width: Optional[int] = None,
                 text: Optional[str] = None, no_preview: Optional[bool] = None, parse_mode: Optional[str] = None,
                 silent: Optional[bool] = None, validation_error: Optional[str] = None,
                 extras: Optional[Dict[str, Any]] = None, keyboard_values_to_format: Optional[List[str]] = None,
                 markup_type: Optional[str] = None, prev_menu: Optional[str] = None, next_menu: Optional[str] = None,
                 filters: Optional[List[str]] = None, callback_data: Optional[Union[str, int]] = None):
        self.name: str = name
        self.obj: Optional[Union[types.Message, types.CallbackQuery]] = obj
        self._neko: BaseNeko = obj.conf['neko']
        self.markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None

        self.text: Optional[str] = text
        self.no_preview: Optional[bool] = no_preview
        self.parse_mode: Optional[str] = parse_mode
        self.silent: Optional[bool] = silent
        self.raw_markup: Optional[List[List[Dict[str, str]]]] = markup
        self.markup_row_width: Optional[int] = markup_row_width
        self.validation_error: str = validation_error or 'ValidationError'
        self.extras: Dict[str, Any] = extras or dict()
        self.keyboard_values_to_format = keyboard_values_to_format or list(self._default_keyboard_values.keys())
        self.markup_type: Optional[str] = markup_type
        self.prev_menu: Optional[str] = prev_menu
        self.next_menu: Optional[str] = next_menu
        self.filters: Optional[List[str]] = filters
        self._call_data: Optional[Union[str, int]] = callback_data
        self._break_execution: bool = False

    def break_execution(self):
        self._break_execution = True

    @property
    def is_broken(self) -> bool:
        return self._break_execution

    @staticmethod
    def _apply_formatting(formatting: Optional[Union[List[Any], Dict[str, Any], Any]] = None, *items) -> List[str]:
        result = list()
        for item in items:
            if item is None:
                result.append(item)
                continue

            if isinstance(formatting, list):
                result.append(item.format(*formatting))
            elif isinstance(formatting, dict):
                result.append(item.format(**formatting))
            elif formatting is not None:
                result.append(item.format(formatting))
            else:
                result.append(item)
        return result

    async def send_message(self, user_id: Optional[int] = None) -> types.Message:
        if user_id is None:
            user_id = self.obj.from_user.id
        msg = await self.obj.bot.send_message(chat_id=user_id, text=self.text,
                                              parse_mode=self.parse_mode, disable_web_page_preview=self.no_preview,
                                              disable_notification=self.silent, reply_markup=self.markup)
        last_message_id = await self._neko.storage.get_last_message_id(user_id=user_id)
        await self._neko.storage.set_last_message_id(user_id=user_id, message_id=msg.message_id)
        with suppress(Exception):
            await self.obj.bot.delete_message(chat_id=user_id, message_id=last_message_id)
        return msg

    async def edit_text(self) -> types.Message:
        obj = self.obj if isinstance(self.obj, types.Message) else self.obj.message
        msg = await obj.edit_text(text=self.text, parse_mode=self.parse_mode, reply_markup=self.markup,
                                  disable_web_page_preview=self.no_preview)
        if isinstance(self.obj, types.CallbackQuery):
            await self._neko.storage.set_last_message_id(user_id=self.obj.from_user.id, message_id=msg.message_id)
        return msg

    async def _resolve_markup_type(self) -> Type[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]]:
        """
        Resolve markup type
        :return: InlineKeyboardMarkup or ReplyKeyboardMarkup type
        """
        if self.markup_type == 'inline':
            return types.InlineKeyboardMarkup
        elif self.markup_type == 'reply':
            return types.ReplyKeyboardMarkup

        for row in self.raw_markup:  # Guess the type otherwise
            for button in row:
                if any([i in button for i in self._inline_markup_identifiers]):
                    return types.InlineKeyboardMarkup
        return types.ReplyKeyboardMarkup

    async def _format_markup(self, markup: Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup],
                             markup_format: Optional[Union[List[Any], Dict[str, Any], Any]],
                             allowed_buttons: Optional[List[Union[str, int]]]) -> \
            Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]:
        """
        Apply markup format
        :param markup: Base markup object
        :param markup_format: A list, dict or single value to use for formatting
        :param allowed_buttons: A list of allowed button IDs
        :return: A formatted markup object
        """
        filter_buttons: bool = isinstance(allowed_buttons, list)

        button_type = types.InlineKeyboardButton \
            if isinstance(markup, types.InlineKeyboardMarkup) else types.KeyboardButton

        for row in self.raw_markup:  # Fill existing markup
            buttons: Union[List[types.InlineKeyboardButton], List[types.KeyboardButton]] = list()
            for button in row:
                if filter_buttons and button.get('id') is not None and button['id'] not in allowed_buttons:
                    continue  # Button should be ignored

                if button_type == types.InlineKeyboardButton:  # Inline buttons only
                    for key, value in {'call_data': 'callback_data', 'query': 'switch_inline_query',
                                       'cc_query': 'switch_inline_query_current_chat'}.items():  # Apply aliases
                        if button.get(key) is not None:
                            button[value] = button.pop(key)

                    if button.get('url') and button['url'].startswith('@'):
                        button['url'] = button['url'].replace('@', 'https://t.me/')

                if markup_format:  # Apply button formatting
                    for item in self.keyboard_values_to_format:
                        if button.get(item):
                            button[item] = self._apply_formatting(markup_format, button[item])[0]
                buttons.append(button_type(**button))
            markup.add(*buttons)
        return markup

    async def build(self, text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                    markup_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                    markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None,
                    allowed_buttons: List[Union[str, int]] = None):
        """
        Build a menu
        :param text_format: Formatting for menu text
        :param markup_format: Formatting for markup buttons
        :param markup: Aiogram markup object
        :param allowed_buttons: In case of access limitation which buttons to display
        """
        if self.text:
            self.text = self._apply_formatting(text_format, self.text)[0]

        if markup is None and self.raw_markup is not None:
            # Resolve markup type
            markup_type = await self._resolve_markup_type()
            if markup_type == types.ReplyKeyboardMarkup:
                markup = types.ReplyKeyboardMarkup(row_width=self.markup_row_width or 3, resize_keyboard=True)
            else:
                markup = markup_type(row_width=self.markup_row_width or 3)

        if markup:
            self.markup = await self._format_markup(markup=markup, markup_format=markup_format,
                                                    allowed_buttons=allowed_buttons)

    @property
    def call_data(self) -> Optional[Any]:
        return self._call_data

    async def add_pagination(self, offset: int, found: int, limit: int, shift_last: bool = True):
        """
        Add a pagination
        :param offset: Item offset
        :param found: Number of found items found on this page
        :param limit: Max number of items that can be displayed at a time
        :param shift_last: Whether to shift the last button
        """
        if self.markup:
            LOGGER.warning(f'Pagination was not applied for {self.name} since the menu is already built!')
        last_button = self.raw_markup[-1]
        if shift_last:
            del self.raw_markup[-1]
        if offset >= limit and found > limit:
            # Add previous and next buttons
            self.raw_markup.append([{'call_data': f'{self.name}#{offset - limit}', 'text': '⬅️'},
                                    {'call_data': f'{self.name}#{offset + limit}', 'text': '➡️'}])
        elif offset >= limit:
            self.raw_markup.append([{'call_data': f'{self.name}#{offset - limit}', 'text': '⬅️'}])
        elif found > limit:
            self.raw_markup.append([{'call_data': f'{self.name}#{offset + limit}', 'text': '➡️'}])
        if shift_last:
            self.raw_markup.append(last_button)
