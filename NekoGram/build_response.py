from typing import Optional, Union, Dict, List, Any, Callable
from aiogram import types
import NekoGram


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
        self.function: Optional[Callable[[NekoGram.Neko.BuildResponse, Union[types.Message, types.CallbackQuery],
                                          NekoGram.Neko], Any]] = kwargs.get('function')
        self.back_menu: Optional[str] = kwargs.get('back_menu')
        kwargs.pop('back_menu', None)
        kwargs.pop('function', None)
        self.data = self.Data(**kwargs)

    async def answer_menu_call(self, answer: bool = True, answer_only: bool = False):
        self.data.extras['answer_call']: bool = answer
        self.data.extras['answer_only']: bool = answer_only
