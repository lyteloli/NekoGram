from __future__ import annotations

from typing import Optional, Union, Dict, List, Any, Callable
from aiogram import types
import NekoGram


class BuildResponse:
    class Data:
        @staticmethod
        def _apply_formatting(formatting: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                              *items) -> List[str]:
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

        def __init__(self, name: str,
                     markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup,
                                            List[List[Dict[str, str]]]]] = None,
                     text: Optional[str] = None, no_preview: Optional[bool] = None, silent: Optional[bool] = None,
                     markup_row_width: Optional[int] = None, parse_mode: Optional[str] = None,
                     allowed_items: Optional[List[str]] = None, extras: Optional[Dict[str, Any]] = None,
                     markup_type: Optional[str] = None):
            self.name: str = name
            self.text: Optional[str] = text
            self.no_preview: Optional[bool] = no_preview
            self.parse_mode: Optional[str] = parse_mode
            self.silent: Optional[bool] = silent
            self.markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None
            self.markup_row_width: int = markup_row_width or 3
            self.raw_markup: Optional[List[List[Dict[str, str]]]] = markup
            self.extras: Dict[str, Any] = extras or dict()
            self.allowed_items: Optional[List[str]] = allowed_items
            self.markup_type: str = markup_type or 'inline'

        async def assemble_markup(self, text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                                  markup_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                                  markup: Optional[Union[types.InlineKeyboardMarkup,
                                                         types.ReplyKeyboardMarkup]] = None,
                                  permission_level: int = 1):
            """
            Assembles markup
            :param text_format: Formatting for menu text
            :param markup_format: Formatting for markup buttons
            :param markup: Aiogram markup object
            :param permission_level: The level of permissions to access the menu
            """
            if self.text:
                self.text = self._apply_formatting(text_format, self.text)[0]

            if self.raw_markup:
                if markup is None and self.markup_type.lower().startswith('reply'):
                    markup = types.ReplyKeyboardMarkup(row_width=self.markup_row_width, resize_keyboard=True)
                elif markup is None:
                    markup = types.InlineKeyboardMarkup(row_width=self.markup_row_width)

                if isinstance(markup, types.ReplyKeyboardMarkup):
                    for row in self.raw_markup:
                        row_buttons: List[Union[types.InlineKeyboardButton, types.KeyboardButton]] = []
                        for button in row:
                            text: str = self._apply_formatting(markup_format, button.get('text', '!'))[0]

                            button_permission_level: int = button.get('permission_level', 0)
                            if permission_level < button_permission_level:
                                continue

                            row_buttons.append(types.KeyboardButton(text=text))
                        markup.add(*row_buttons)

                else:
                    for row in self.raw_markup:
                        row_buttons: List[Union[types.InlineKeyboardButton, types.KeyboardButton]] = []
                        for button in row:
                            text: str = button.get('text', '!')
                            call_data: Optional[str] = button.get('call_data')
                            url: Optional[str] = button.get('url')
                            if url:
                                if url.startswith('@'):
                                    url = url.replace('@', 'https://t.me/')
                                elif not url.startswith(('http://', 'https://')):
                                    raise ValueError('Markup URLs have to start with http:// or https://')

                            elif call_data is None:
                                raise ValueError('Inline keyboards can\'t contain text buttons (call and url are None)')

                            button_permission_level: int = button.get('permission_level', 0)
                            if permission_level < button_permission_level:
                                continue

                            text, call_data, url = self._apply_formatting(markup_format, text, call_data, url)

                            if url:
                                row_buttons.append(types.InlineKeyboardButton(text=text, url=url))
                            else:
                                row_buttons.append(types.InlineKeyboardButton(text=text, callback_data=call_data))
                        markup.add(*row_buttons)

            self.markup = markup

        @property
        def call_data(self) -> Optional[str]:
            return self.extras.get('call_data')

        async def add_pagination(self, offset: int, found: int, limit: int):
            """
            Add a pagination
            :param offset: Item offset
            :param found: Number of found items found on this page
            :param limit: Max number of items that can be displayed at a time
            """
            if offset >= limit and found > limit:
                # Add previous and next buttons
                self.raw_markup.append([{f'{self.name}#{offset - limit}': '⬅️', f'{self.name}#{offset + limit}': '➡️'}])
            elif offset >= limit:
                self.raw_markup.append([{f'{self.name}#{offset - limit}': '⬅️'}])
            elif found > limit:
                self.raw_markup.append([{f'{self.name}#{offset + limit}': '➡️'}])

    def __init__(self, **kwargs):
        self.function: Optional[Callable[[BuildResponse, Union[types.Message, types.CallbackQuery],
                                          NekoGram.Neko], Any]] = kwargs.get('function')
        self.back_menu: Optional[str] = kwargs.get('back_menu')
        kwargs.pop('back_menu', None)
        kwargs.pop('function', None)
        self.data = self.Data(**kwargs)

    def answer_menu_call(self, answer: bool = True, answer_only: bool = False):
        """
        Answer a CallbackQuery (formatters only)
        :param answer: Whether to answer the call
        :param answer_only: Whether to only answer the call
        """
        self.data.extras['answer_call']: bool = answer
        self.data.extras['answer_only']: bool = answer_only

    def delete_and_send(self):
        """
        Deletes the current message and sends a new one
        """
        self.data.extras['delete_and_send'] = True
