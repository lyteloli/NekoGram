from typing import Union, Optional, Dict, Any, AsyncGenerator, List, Tuple, Iterable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod


class BaseStorage(ABC):
    def __init__(self, default_language: str = 'en'):
        self.default_language: str = default_language
        self._cached_user_languages: Dict[str, Dict[str, Union[str, datetime]]] = dict()

    @abstractmethod
    def p(self, counter: Optional[int] = None) -> str:
        """
        Returns a placeholder for a query argument, e.g. `%s`, `?` or `$X`.
        """

    @abstractmethod
    async def set_user_language(self, user_id: int, language: str) -> None:
        self._cached_user_languages[str(user_id)] = {
            'date': datetime.now(), 'lang': language
        }

    @abstractmethod
    async def get_user_language(self, user_id: int) -> str:
        pass

    async def get_cached_user_language(self, user_id: Union[int, str]) -> Optional[str]:
        user_id = str(user_id)
        if (user_id in self._cached_user_languages.keys() and
                self._cached_user_languages[user_id]['date'] + timedelta(minutes=20) > datetime.now()):
            return self._cached_user_languages[user_id]['lang']

    @abstractmethod
    async def set_user_data(
            self,
            user_id: int,
            data: Optional[Dict[str, Any]] = None,
            replace: bool = False,
            bot_token: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_user_data(self, user_id: int, bot_token: Optional[str] = None) -> Dict[str, Any]:
        pass

    async def set_user_menu(self, user_id: int, menu: Optional[str] = None, bot_token: Optional[str] = None) -> str:
        await self.set_user_data(user_id=user_id, data={'menu': menu})
        return menu

    async def get_user_menu(self, user_id: int, bot_token: Optional[str] = None) -> str:
        data = await self.get_user_data(user_id=user_id)
        return data.get('menu')

    @abstractmethod
    async def check_user_exists(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def set_last_message_id(self, user_id: int, message_id: int) -> None:
        pass

    @abstractmethod
    async def get_last_message_id(self, user_id: int) -> Optional[int]:
        pass

    @abstractmethod
    async def create_user(
            self,
            user_id: int,
            name: str,
            username: Optional[str],
            language: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    async def apply(
            self,
            query,
            args: Union[Tuple[Any, ...], Dict[str, Any], Any] = (),
            ignore_errors: bool = False
    ) -> int:
        pass

    async def select(
            self,
            query,
            args: Union[Tuple[Any, ...], Dict[str, Any], Any] = ()
    ) -> AsyncGenerator[Union[Dict[str, Any], '_AttrDict'], None]:
        yield

    @abstractmethod
    async def get(
            self,
            query: str,
            args: Union[Tuple[Any, ...], Dict[str, Any], Any] = (),
            fetch_all: bool = False,
            use_attr_dict: bool = True
    ) -> Union[bool, List[Dict[str, Any]], Dict[str, Any], '_AttrDict']:
        pass

    @abstractmethod
    async def check(self, query: str, args: Union[Tuple[Any, ...], Dict[str, Any], Any] = ()) -> int:
        pass

    @abstractmethod
    async def acquire_pool(self) -> bool:
        pass

    @abstractmethod
    async def close_pool(self) -> bool:
        pass

    async def add_tables(self, structure: Dict[str, Dict[str, Dict[str, Optional[str]]]], required_by: str):
        pass

    @staticmethod
    def _verify_args(args: Any) -> Tuple[Any, ...]:
        if not isinstance(args, (tuple, dict)):
            args = (args,)
        return args

    class _AttrDict(dict):
        def __dir__(self) -> Iterable[str]:
            return list(super().__dir__()) + [str(k) for k in self.keys()]

        def __getattr__(self, item: str) -> Any:
            if item in self:
                return self[item]
            raise AttributeError(f'type object \'AttrDict\' has no attribute \'{item}\'')

        def __getattribute__(self, item: str) -> Any:
            try:
                return super().__getattribute__(item)
            except AttributeError:
                return self.__getattr__(item)

        def __setattr__(self, key: str, value: Any):
            self[key] = value
