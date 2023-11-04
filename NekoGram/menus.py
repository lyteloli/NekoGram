from typing import Optional, Union, Dict, List, Any, Type, Set, Iterable
from aiogram import types, exceptions as aiogram_exc
from typing_extensions import deprecated  # noqa
from contextlib import suppress
from io import BytesIO

from .utils import NekoGramWarning
from .base_neko import BaseNeko
from .logger import LOGGER


class Menu:
    __default_keyboard_values: Dict[str, str] = {
        'callback_data': 'call_data',
        'switch_inline_query': 'query',
        'switch_inline_query_current_chat': 'cc_query',
        'text': 'text',
        'url': 'url',
        'menu': 'call_data'
    }
    __default_menu_values: Dict[str, str] = {'caption': 'text'}
    __inline_markup_identifiers: List[str] = [
        'call_data',
        'callback_data',
        'query',
        'switch_inline_query',
        'cc_query',
        'switch_inline_query_current_chat',
        'url'
    ]
    __media_extensions: Dict[str, Set[str]] = {
        'photo': {'jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp', 'heif', 'svg', 'eps'},
        'video': {
            'mpg', 'mp2', 'mpeg', 'mpe', 'mpv', 'ogg', 'mp4', 'm4v', 'avi', 'wmv', 'mov', 'qt', 'flv', 'swf', 'avchd'
        },
        'audio': {
            '3gp', 'aa', 'aac', 'aax', 'act', 'aiff', 'alac', 'amr', 'ape', 'au', 'awb', 'dss', 'dvf', 'flac',
            'gsm', 'iklax', 'ivs', 'm4a', 'm4b', 'mmf', 'mp3', 'mpc', 'msv', 'ogg', 'oga', 'mogg', 'opus', 'ra',
            'rm', 'rf64', 'sln', 'tta', 'voc', 'vox', 'wav', 'wma', 'wv', '8svx', 'cda'
        },
        'animation': {'gif', 'webm'},
        'document': set()
    }

    __cached_media: Dict[str, bytes] = dict()

    def __init__(
            self,
            name: str,
            obj: Union[types.Message, types.CallbackQuery, types.InlineQuery],
            markup: Optional[List[List[Dict[str, str]]]] = None,
            markup_row_width: Optional[int] = None,
            text: Optional[str] = None,
            no_preview: Optional[bool] = None,
            parse_mode: Optional[str] = None,
            silent: Optional[bool] = None,
            validation_error: Optional[str] = None,
            keyboard_values_to_format: Optional[List[str]] = None,
            markup_type: Optional[str] = None,
            prev_menu: Optional[str] = None,
            next_menu: Optional[str] = None,
            filters: Optional[List[str]] = None,
            callback_data: Optional[Union[str, int]] = None,
            bot_token: Optional[str] = None,
            intermediate_menu: Optional[str] = None,
            media: Optional[str] = None,
            media_type: Optional[str] = None,
            media_spoiler: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            **kwargs
    ):
        self.name: str = name
        self.obj: Optional[Union[types.Message, types.CallbackQuery, types.InlineQuery]] = obj
        self.neko: BaseNeko = obj.conf['neko']
        self.markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None

        self.text: Optional[str] = text
        self._init_media: Optional[Union[str, BytesIO]] = media
        self._media: Optional[Union[str, BytesIO]] = media
        self._media_type: Optional[str] = media_type
        self.media_spoiler: Optional[bool] = media_spoiler
        self.protect_content: Optional[bool] = protect_content
        self.no_preview: Optional[bool] = no_preview
        self.parse_mode: Optional[str] = parse_mode
        self.silent: Optional[bool] = silent
        self.raw_markup: Optional[List[List[Dict[str, str]]]] = markup
        self.markup_row_width: Optional[int] = markup_row_width
        self.validation_error: str = validation_error or 'ValidationError'
        self.extras: Dict[str, Any] = kwargs.pop('extras', dict())
        self.keyboard_values_to_format = keyboard_values_to_format or list(self.__default_keyboard_values.keys())
        self.markup_type: Optional[str] = markup_type
        self.prev_menu: Optional[str] = prev_menu
        self.next_menu: Optional[str] = next_menu
        self.filters: Optional[List[str]] = filters
        self._call_data: Optional[Union[str, int]] = callback_data
        self.bot_token: Optional[str] = bot_token
        self.bot_id: Optional[int] = None
        self.intermediate_menu: Optional[str] = intermediate_menu
        self._break_execution: bool = False
        self.skip_media_validation: bool = False

        self.extras.update(kwargs)

        if self.bot_token:
            self.bot_id = int(self.bot_token.split(':')[0])

        self.validate_media()

    def validate_media(self) -> None:
        """
        Validate and process media.
        """
        if self.skip_media_validation or not self.media:
            return
        if self._media_type and self._media_type not in self.__media_extensions.keys():
            raise ValueError(
                f'{self._media_type} is not a valid media type (defined in {self.name}). '
                f'Valid options: {", ".join(self.__media_extensions.keys())}'
            )
        else:
            self._media_type = self.resolve_media_type(self._media)
        self.resolve_media()

    @classmethod
    def resolve_media_type(cls, path_or_url: str) -> str:
        part: str = path_or_url.split('.')[-1].lower().split('?')[0]
        for key, value in cls.__media_extensions.items():
            if part in value:
                return key
        return 'document'

    def resolve_media(self) -> None:
        if self.skip_media_validation or self._init_media.startswith(('http://', 'https://')):  # noqa
            return
        if not self.__cached_media.get(self._init_media):
            with open(self._init_media, 'rb') as f:
                self.__cached_media[self._init_media] = f.read()
        self._media = BytesIO(self.__cached_media[self._init_media])

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, value: Optional[str]):
        self._init_media = value
        self._media = value
        self.validate_media()

    @property
    def media_type(self):
        return self._media_type

    @media_type.setter
    def media_type(self, value: str):
        self._media_type = value.lower()
        self.validate_media()

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

    async def send_message(self, user_id: Optional[int] = None, ignore_media: bool = False) -> types.Message:
        """
        Sends the menu as a message to a user.
        :param user_id: Telegram user ID.
        :param ignore_media: Whether to ignore media defined in the menu.
        :return: Sent message.
        """
        if user_id is None:
            user_id = self.obj.from_user.id
        if self.media and not ignore_media:
            msg = await getattr(self.obj.bot, f'send_{self._media_type}')(**{
                self.media_type: self.media,
                'chat_id': user_id,
                'caption': self.text,
                'parse_mode': self.parse_mode,
                'disable_notification': self.silent,
                'reply_markup': self.markup,
                'protect_content': self.protect_content
            })
        else:
            msg = await self.obj.bot.send_message(
                chat_id=user_id,
                text=self.text,
                protect_content=self.protect_content,
                parse_mode=self.parse_mode,
                disable_web_page_preview=self.no_preview,
                disable_notification=self.silent,
                reply_markup=self.markup,
            )
        if self.neko.delete_messages:
            last_message_id = await self.neko.storage.get_last_message_id(user_id=user_id)
            await self.neko.storage.set_last_message_id(user_id=user_id, message_id=msg.message_id)
            with suppress(Exception):
                await self.obj.bot.delete_message(chat_id=user_id, message_id=last_message_id)
        return msg

    async def edit_message(self, ignore_media: bool = False) -> types.Message:
        """
        Edits message with menu properties.
        :param ignore_media: Whether to ignore media defined in the menu.
        :return: Edited message.
        """
        obj = self.obj if isinstance(self.obj, types.Message) else self.obj.message
        if self.media:
            if ignore_media:
                msg = await obj.edit_caption(caption=self.text, parse_mode=self.parse_mode, reply_markup=self.markup)
            else:
                try:
                    msg = await obj.edit_media(
                        media=getattr(types, f'InputMedia{self._media_type.capitalize()}')(
                            media=self.media,
                            caption=self.text,
                            parse_mode=self.parse_mode,
                            has_spoiler=self.media_spoiler
                        ),
                        reply_markup=self.markup
                    )
                except aiogram_exc.BadRequest as e:
                    if str(e) == 'There is no media in the message to edit':
                        try:
                            await obj.delete()
                        except Exception:  # noqa
                            await obj.edit_reply_markup()
                        self.resolve_media()
                        msg = await getattr(obj, f'answer_{self._media_type}')(**{
                            self._media_type: self.media,
                            'caption': self.text,
                            'parse_mode': self.parse_mode,
                            'reply_markup': self.markup
                        })
                    else:
                        raise e
        else:
            msg = await obj.edit_text(
                text=self.text,
                parse_mode=self.parse_mode,
                reply_markup=self.markup,
                disable_web_page_preview=self.no_preview
            )
        if isinstance(self.obj, types.CallbackQuery):
            await self.neko.storage.set_last_message_id(user_id=self.obj.from_user.id, message_id=msg.message_id)
        return msg

    @deprecated(
        'The `edit_text` method is deprecated and may be removed in future updates, use `edit_message` instead.',
        category=NekoGramWarning
    )
    async def edit_text(self, ignore_media: bool = False) -> types.Message:
        return await self.edit_message(ignore_media=ignore_media)

    def build_inline_query_result_args(self, **kwargs) -> Dict[str, Any]:
        """
        Builds kwargs for InlineQueryResult with menu and custom properties.
        :param kwargs: Custom properties for InlineQueryResult.
        :return: Kwargs to initialize an InlineQueryResult object.
        """
        return dict(caption=self.text, parse_mode=self.parse_mode, reply_markup=self.markup, **kwargs)

    async def _resolve_markup_type(self) -> Type[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]]:
        """
        Resolve markup type.
        :return: InlineKeyboardMarkup or ReplyKeyboardMarkup type.
        """
        if self.markup_type == 'inline':
            return types.InlineKeyboardMarkup
        elif self.markup_type == 'reply':
            return types.ReplyKeyboardMarkup

        for row in self.raw_markup:  # Guess the type otherwise
            for button in row:
                if any([i in button for i in self.__inline_markup_identifiers]):
                    return types.InlineKeyboardMarkup
        return types.ReplyKeyboardMarkup

    async def _format_markup(
            self,
            markup: Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup],
            markup_format: Optional[Union[List[Any], Dict[str, Any], Any]],
            allowed_buttons: Optional[Iterable[Union[str, int]]]
    ) -> Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]:
        """
        Apply markup format.
        :param markup: Base markup object.
        :param markup_format: A list, dict or single value to use for formatting.
        :param allowed_buttons: An iterable of allowed button IDs.
        :return: A formatted markup object.
        """
        filter_buttons: bool = isinstance(allowed_buttons, Iterable) and not isinstance(allowed_buttons, str)

        button_type = types.InlineKeyboardButton \
            if isinstance(markup, types.InlineKeyboardMarkup) else types.KeyboardButton

        for row in self.raw_markup:  # Fill existing markup
            buttons: Union[List[types.InlineKeyboardButton], List[types.KeyboardButton]] = list()
            for button in row:
                if filter_buttons and button.get('id') is not None and button['id'] not in allowed_buttons:
                    continue  # Button should be ignored

                if button_type == types.InlineKeyboardButton:  # Inline buttons only
                    for key, value in {
                        'call_data': 'callback_data',
                        'query': 'switch_inline_query',
                        'cc_query': 'switch_inline_query_current_chat'
                    }.items():  # Apply aliases
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

    async def build(
            self,
            text_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
            markup_format: Optional[Union[List[Any], Dict[str, Any], Any]] = None,
            markup: Optional[Union[types.InlineKeyboardMarkup, types.ReplyKeyboardMarkup]] = None,
            allowed_buttons: Iterable[Union[str, int]] = None,
            skip_field_validation: bool = False
    ):
        """
        Build a menu.
        :param text_format: Formatting for menu text.
        :param markup_format: Formatting for markup buttons.
        :param markup: Aiogram markup object.
        :param allowed_buttons: In case of access limitation which buttons to display.
        :param skip_field_validation: Whether to skip menu field validation (not recommended).
        """

        if not skip_field_validation:  # Validate extras
            for key, value in self.extras.items():
                if key in self.__default_menu_values:
                    setattr(self, self.__default_menu_values[key], value)

        if self.text:
            self.text = self._apply_formatting(text_format, self.text)[0]

        if markup is None and self.raw_markup is not None:  # Resolve markup type
            markup_type = await self._resolve_markup_type()
            if markup_type == types.ReplyKeyboardMarkup:
                markup = types.ReplyKeyboardMarkup(row_width=self.markup_row_width or 3, resize_keyboard=True)
            else:
                markup = markup_type(row_width=self.markup_row_width or 3)

        if markup:
            self.markup = await self._format_markup(
                markup=markup,
                markup_format=markup_format,
                allowed_buttons=allowed_buttons
            )

    @property
    def call_data(self) -> Optional[Any]:
        return self._call_data

    async def add_pagination(
            self,
            offset: int,
            found: int,
            limit: int,
            shift_last: int = 1,
            prev: str = '⬅️',
            next: str = '➡️',  # noqa
    ) -> None:
        """
        Add a pagination.
        :param offset: Item offset.
        :param found: Number of found items found on this page.
        :param limit: Max number of items that can be displayed at a time.
        :param shift_last: Number of buttons to shift starting from the end.
        :param prev: text for a button which leads to the previous page.
        :param next: text for a button which leads to the next page.
        """
        if self.markup:
            return LOGGER.warning(f'Pagination was not applied for {self.name} since the menu is already built!')
        index_to_insert = len(self.raw_markup) - shift_last
        if offset >= limit and found > limit:
            self.raw_markup[index_to_insert: index_to_insert] = [[
                {'call_data': f'{self.name}#{offset - limit}', 'text': prev},
                {'call_data': f'{self.name}#{offset + limit}', 'text': next}
            ]]
        elif offset >= limit:
            self.raw_markup[index_to_insert: index_to_insert] = [[
                {'call_data': f'{self.name}#{offset - limit}', 'text': prev}
            ]]
        elif found > limit:
            self.raw_markup[index_to_insert: index_to_insert] = [[
                {'call_data': f'{self.name}#{offset + limit}', 'text': next}
            ]]
