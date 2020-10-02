from typing import Union, Optional, Dict, Any, AsyncGenerator, List


class BaseStorage:
    def __init__(self, default_language: str = 'en'):
        self.users: Dict[str, Dict[str, Any]] = dict()
        self.default_language: str = default_language

    async def set_user_language(self, user_id: int, language: str):
        if not self.users.get(str(user_id)):  # Check if user exists so it won't fail
            self.users[str(user_id)] = {}

        self.users[str(user_id)]['language'] = language

    async def get_user_language(self, user_id: int) -> str:
        return self.users.get(str(user_id), {}).get('language', self.default_language)

    async def set_user_data(self, user_id: int, data: Optional[Dict[str, Any]] = None,
                            replace: bool = False) -> Dict[str, Any]:
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

        return user_data

    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        return self.users.get(str(user_id), {}).get('data', {})

    async def check_user_exists(self, user_id: int) -> bool:
        return bool(self.users.get(str(user_id)))

    async def create_user(self, user_id: int, language: Optional[str] = None):
        if language is None:
            language = self.default_language

        self.users[str(user_id)] = {'language': language}

    async def apply(self, query, args=None):
        pass

    async def select(self, query, args=None) -> AsyncGenerator[Dict[str, Any], None]:
        yield

    async def get(self, query: str, args=None, fetch_all: bool = False) -> Union[bool, List[Dict[str, Any]],
                                                                                 Dict[str, Any]]:
        pass

    async def check(self, query: str, args=None) -> int:
        pass
