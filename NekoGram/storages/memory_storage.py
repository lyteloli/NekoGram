from typing import Union, Optional, Dict, Any, AsyncGenerator, List
from .base_storage import BaseStorage
from ..logger import LOGGER


class MemoryStorage(BaseStorage):
    def __init__(self, default_language: str = 'en'):
        super().__init__(default_language=default_language)
        self._message_history: Dict[str, int] = dict()

    async def set_user_language(self, user_id: int, language: str):
        await super().set_user_language(user_id=user_id, language=language)
        if not self.users.get(str(user_id)):  # Check if user exists so it won't fail
            self.users[str(user_id)] = {}

        self.users[str(user_id)]['language'] = language
        LOGGER.info(f'Set language to {language} for {user_id}')

    async def get_user_language(self, user_id: int) -> str:
        lang = self.users.get(str(user_id), {}).get('language', self.default_language)
        await super().set_user_language(user_id=user_id, language=lang)
        LOGGER.info(f'Retrieved language for {user_id}: {lang}')
        return lang

    async def set_user_data(self, user_id: int, data: Optional[Dict[str, Any]] = None,
                            replace: bool = False, bot_token: Optional[str] = None) -> Dict[str, Any]:
        if data is None:
            data = dict()
            replace = True

        if replace:
            user_data = data
        else:
            user_data = await self.get_user_data(user_id=user_id)
            user_data.update(data)

        if not self.users.get(str(user_id)):  # Check if user exists so it won't fail
            self.users[str(user_id)] = {}

        self.users[str(user_id)]['data'] = user_data
        LOGGER.info(f'Set user data for {user_id}: {user_data}')
        return user_data

    async def get_user_data(self, user_id: int, bot_token: Optional[str] = None) -> Dict[str, Any]:
        data = self.users.get(str(user_id), {}).get('data', {})
        LOGGER.info(f'Fetched user data for {user_id}: {data}')
        return data

    async def set_user_menu(self, user_id: int, menu: Optional[str] = None, bot_token: Optional[str] = None):
        await self.set_user_data(user_id=user_id, data={'menu': menu})
        return menu

    async def get_user_menu(self, user_id: int, bot_token: Optional[str] = None) -> Optional[str]:
        return (await self.get_user_data(user_id=user_id)).get('menu')

    async def check_user_exists(self, user_id: int) -> bool:
        exists: bool = bool(self.users.get(str(user_id)))
        LOGGER.info(f'Checked existence of {user_id}: {exists}')
        return exists

    async def set_last_message_id(self, user_id: int, message_id: int):
        LOGGER.info(f'Set last message ID for {user_id}: {message_id}')
        self._message_history[str(user_id)] = message_id

    async def get_last_message_id(self, user_id: int) -> Optional[int]:
        message_id = self._message_history.get(str(user_id))
        LOGGER.info(f'Retrieved last message ID for {user_id}: {message_id}')
        return message_id

    async def create_user(self, user_id: int, language: Optional[str] = None):
        if language is None:
            language = self.default_language

        self.users[str(user_id)] = {'language': language}
        LOGGER.info(f'Created a new user: {user_id}, {language}')

    async def apply(self, query, args=None):
        pass

    async def select(self, query, args=None) -> AsyncGenerator[Dict[str, Any], None]:
        yield

    async def get(self, query: str, args=None, fetch_all: bool = False) -> Union[bool, List[Dict[str, Any]],
                                                                                 Dict[str, Any]]:
        pass

    async def check(self, query: str, args=None) -> int:
        pass
