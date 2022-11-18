from aiogram.dispatcher.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Dict, List, Any, Union, Optional
from .storages.base_storage import BaseStorage
import re


class HasMenu(Filter):
    def __init__(self, database: BaseStorage):
        self.database: BaseStorage = database

    @classmethod
    def validate(cls, _: Dict[str, Any]):
        return {}

    async def check(self, obj: Union[Message, CallbackQuery]) -> bool:
        return bool((await self.database.get_user_data(user_id=obj.from_user.id)).get('menu', False))


class StartsWith(Filter):
    """
    Filter for checking if message text or callback query starts with a certain text
    """

    def __init__(self, starts_with: Optional[Union[List[str], str]] = None):
        if not starts_with:
            raise ValueError('Text to start with is not specified!')

        self.starts_with: List[str] = starts_with if isinstance(starts_with, list) else [starts_with]

    @classmethod
    def validate(cls, _: Dict[str, Any]):
        return {}

    async def check(self, obj: Union[Message, CallbackQuery]) -> bool:
        for text in self.starts_with:
            if isinstance(obj, Message) and obj.text.startswith(text):
                return True
            elif isinstance(obj, CallbackQuery) and obj.data.startswith(text):
                return True
            return False

        return False


class BuiltInFilters:
    @staticmethod
    async def _to_message(obj: Union[Message, CallbackQuery]) -> Message:
        if isinstance(obj, CallbackQuery):
            obj = obj.message
        return obj

    @staticmethod
    async def is_any(_: Union[Message, CallbackQuery]) -> bool:
        """
        Check if message is of any content types available
        :return: Always True
        """
        return True

    async def is_int(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text can be converted to an integer
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and obj.text.isdigit()

    @staticmethod
    async def is_int_neg(obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text can be converted to a negative integer
        :return: True if so
        """
        try:
            return int(obj.text) < 0
        except ValueError:
            return False

    @staticmethod
    async def is_int_pos(obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text can be converted to a positive integer
        :return: True if so
        """
        try:
            return int(obj.text) > 0
        except ValueError:
            return False

    async def is_float(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text can be converted to a float
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and obj.text.isnumeric()

    async def is_text(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message content is text
        :return: True if so
        """
        obj = await self._to_message(obj)
        return bool(obj.text)

    async def is_photo(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message content is a photo
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.content_type == 'photo'

    async def is_video(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message content is a video
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.content_type == 'video'

    async def is_animation(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message content is a GIF
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.content_type == 'animation'

    async def is_http_url(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is an HTTP URL
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'http://[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:'
                                         r'[-a-zA-Z0-9()@:%_+.~#?&/=]*)$', obj.text)

    async def is_https_url(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is an HTTPS URL
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'https://[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:'
                                         r'[-a-zA-Z0-9()@:%_+.~#?&/=]*)$', obj.text)

    async def is_tg_url(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is a Telegram URL
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'tg://[-a-zA-Z0-9_?=]+', obj.text)

    async def is_mention(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is a Telegram user mention
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'@[a-zA-Z0-9_]+', obj.text)

    async def is_url(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is an HTTP/HTTPS/Telegram URL
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'(http|https|tg)://[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:'
                                         r'[-a-zA-Z0-9()@:%_+.~#?&/=]*)$', obj.text)

    async def is_email(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is an email
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', obj.text)

    async def is_phone_number(self, obj: Union[Message, CallbackQuery]) -> bool:
        """
        Checks if message text is an international phone number
        :return: True if so
        """
        obj = await self._to_message(obj)
        return obj.text and re.fullmatch(r'\+([0-9]+\s*)?([0-9]+)?[\s0-9\-]+[0-9]+', obj.text)

    @staticmethod
    async def is_forwarded(obj: Union[Message, CallbackQuery]) -> bool:
        if not isinstance(obj, Message):
            return False

        return bool(obj.forward_from or obj.forward_from_chat)

    @staticmethod
    async def is_forwarded_from_group(obj: Union[Message, CallbackQuery]) -> bool:
        if not isinstance(obj, Message):
            return False

        return obj.forward_from_chat and obj.forward_from_chat.type in ['group', 'supergroup']

    @staticmethod
    async def is_forwarded_from_channel(obj: Union[Message, CallbackQuery]) -> bool:
        if not isinstance(obj, Message):
            return False

        return obj.forward_from_chat and obj.forward_from_chat.type == 'channel'

    @staticmethod
    async def is_forwarded_from_user(obj: Union[Message, CallbackQuery]) -> bool:
        if not isinstance(obj, Message):
            return False

        return bool(obj.forward_from)

    @property
    def to_list(self):
        return [method.replace('is_', '') for method in dir(self) if not method.startswith(('_', 'to_list'))]
