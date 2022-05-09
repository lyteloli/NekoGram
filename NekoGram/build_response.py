from __future__ import annotations

from typing import Optional, Union, Dict, List, Any, Callable
from contextlib import suppress
from aiogram import exceptions
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
                     text: Optional[str] = None, alt_text: Optional[str] = None, no_preview: Optional[bool] = None,
                     silent: Optional[bool] = None, markup_row_width: Optional[int] = None,
                     parse_mode: Optional[str] = None, allowed_items: Optional[List[str]] = None,
                     extras: Optional[Dict[str, Any]] = None, markup_type: Optional[str] = None,
                     filter_args: Optional[List[str]] = None, wrong_content_type_text: Optional[str] = None):
            self.name: str = name
            self.text: Optional[str] = text
            self.alt_text: Optional[str] = alt_text
            self.no_preview: Optional[bool] = no_preview
            self.parse_mode: Optional[str] = parse_mode
            self.silent: Optional[bool] = silent
            self.markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None
            self.markup_row_width: int = markup_row_width or 3
            self.raw_markup: Optional[List[List[Dict[str, str]]]] = markup
            self.extras: Dict[str, Any] = extras or dict()
            self.allowed_items: Optional[List[str]] = allowed_items
            self.markup_type: str = markup_type or 'inline'
            self.filter_args: List[Any] = filter_args or list()
            self.wrong_content_type_text: Optional[str] = wrong_content_type_text

        async def send_message(self, user_id: int, neko: NekoGram.Neko) -> NekoGram.types.Message:
            last_message_id = await neko.storage.get_last_message_id(user_id=user_id)
            message = await neko.bot.send_message(chat_id=user_id, text=self.text, parse_mode=self.parse_mode,
                                                  disable_web_page_preview=self.no_preview,
                                                  disable_notification=self.silent, reply_markup=self.markup)
            await neko.storage.set_last_message_id(user_id=user_id, message_id=message.message_id)

            if last_message_id:
                try:  # Message may not exist
                    await neko.bot.edit_message_reply_markup(chat_id=user_id, message_id=last_message_id)
                except exceptions.MessageCantBeEdited:
                    with suppress(exceptions.TelegramAPIError):
                        await neko.bot.delete_message(chat_id=user_id, message_id=last_message_id)
                except Exception as e:
                    print(f'{last_message_id}: {e}')

            return message

        async def edit_text(self, message: NekoGram.types.Message):
            await message.edit_text(text=self.text, parse_mode=self.parse_mode, reply_markup=self.markup,
                                    disable_web_page_preview=self.no_preview)

        async def assemble_markup(self, text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                                  markup_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
                                  markup: Optional[Union[types.InlineKeyboardMarkup,
                                                         types.ReplyKeyboardMarkup]] = None,
                                  allowed_buttons: List[Union[str, int]] = None):
            """
            Assembles markup
            :param text_format: Formatting for menu text
            :param markup_format: Formatting for markup buttons
            :param markup: Aiogram markup object
            :param allowed_buttons: In case of access limitation which buttons to display
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
                            button_id: str = button.get('id')

                            if allowed_buttons is not None and button_id is not None \
                                    and button_id not in allowed_buttons:
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
                            query: Optional[str] = button.get('query')
                            cc_q: Optional[str] = button.get('cc_query')
                            if url:
                                if url.startswith('@'):
                                    url = url.replace('@', 'https://t.me/')

                            button_id = button.get('id')

                            if allowed_buttons is not None and button_id is not None \
                                    and button_id not in allowed_buttons:
                                continue

                            text, call_data, url = self._apply_formatting(markup_format, text, call_data, url)

                            if url:
                                row_buttons.append(types.InlineKeyboardButton(text=text, url=url))
                            elif cc_q is not None:
                                row_buttons.append(types.InlineKeyboardButton(text=text,
                                                                              switch_inline_query_current_chat=cc_q))
                            elif query:
                                row_buttons.append(types.InlineKeyboardButton(text=text, switch_inline_query=query))
                            else:
                                row_buttons.append(types.InlineKeyboardButton(text=text, callback_data=call_data))
                        markup.add(*row_buttons)

            self.markup = markup

        @property
        def call_data(self) -> Optional[str]:
            return self.extras.get('call_data')

        async def add_pagination(self, offset: int, found: int, limit: int, shift_last: bool = True):
            """
            Add a pagination
            :param offset: Item offset
            :param found: Number of found items found on this page
            :param limit: Max number of items that can be displayed at a time
            :param shift_last: Whether to shift the last button
            """
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
