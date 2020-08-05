from aiogram.dispatcher.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Dict, List, Any, Union, Optional
from .storages.base_storage import BaseStorage


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
    Filter for checking if message text or callback query startswith certain text
    """

    def __init__(self, starts_with: Optional[Union[List[str], str]] = None):
        if not starts_with:
            raise ValueError('Text to start with not specified!')

        self.starts_with: List[str] = starts_with if isinstance(starts_with, list) else [starts_with]

    @classmethod
    def validate(cls, _: Dict[str, Any]):
        return {}

    async def check(self, obj: Union[Message, CallbackQuery]) -> bool:
        for text in self.starts_with:
            if isinstance(obj, Message):
                if obj.text.startswith(text):
                    return True
            elif isinstance(obj, CallbackQuery):
                if obj.data.startswith(text):
                    return True
            else:
                return False

        return False
