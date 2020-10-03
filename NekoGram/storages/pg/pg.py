from typing import Optional, Union, Any, AsyncGenerator, List, Dict, Tuple

try:
    from psycopg2.extras import DictCursor
except ImportError:
    raise ImportError('Install aiopg to use PGStorage!')

from ..base_storage import BaseStorage
from aiopg.sa import create_engine
from psycopg2 import Error
import asyncio

try:
    import ujson as json
except ImportError:
    import json


class PGStorage(BaseStorage):
    def __init__(self, database: str, host: str = 'localhost', port: int = 5432, user: str = 'root',
                 password: Optional[str] = None, create_pool: bool = True, default_language: str = 'en'):
        """
        Initialize database
        :param database: Database name
        :param host: Database host
        :param port: Database port
        :param user: Database user
        :param password: Database password
        :param create_pool: Set True if you want to obtain a pool immediately
        """

        self.engine = None
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.password: str = password
        self.database = database
        self.connection = None

        self.default_language = default_language

        if create_pool:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.acquire_engine())
        super().__init__()

    def __del__(self):
        self.engine.terminate()
        await self.engine.wait_closed()

    async def acquire_engine(self):
        """
        Creates a new PostgreSQL engine
        """
        if self.engine:
            self.engine.terminate()
            await self.engine.wait_closed()

        self.engine = await create_engine(
            user=self.user,
            password=self.password,
            database=self.database,
            host=self.host,
            post=self.port
        )
        self.connection = await self.engine.acquire()

    @staticmethod
    def _verify_args(args: Optional[Union[Tuple[Union[Any, Dict[str, Any]], ...], Any]]):
        if args is None:
            args = tuple()
        if not isinstance(args, (tuple, dict)):
            args = (args,)
        return args

    async def apply(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None):
        """
        Executes SQL query and returns the number of affected rows
        :param query: SQL query to execute
        :param args: Arguments passed to the SQL query
        :return: Number of affected rows
        """
        args = self._verify_args(args)
        try:
            result = await self.connection.execute(query, args)
            return await result.fetchone()
        except Error:
            return 0

    async def select(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> \
            AsyncGenerator[Dict[str, Any], None]:
        """
        Generator that yields rows
        :param query: SQL query to execute
        :param args: Arguments passed to the SQL query
        :return: Yields rows one by one
        """
        args = self._verify_args(args)
        try:
            async for row in self.connection.execute(query, args):
                yield row
        except Error:
            pass

    async def get(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None,
                  fetch_all: bool = False) -> Union[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get a single row or a list of rows from the database
        :param query: SQL query to execute
        :param args: Arguments passed to the SQL query
        :param fetch_all: Set True if you need a list of rows instead of just a single row
        :return: A row or a list or rows
        """
        args = self._verify_args(args)
        try:
            result = await self.connection.execute(query, args)
            if fetch_all:
                return await result.fetchall()
            else:
                return await result.fetchone()
        except Error:
            return False

    async def check(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> int:
        args = self._verify_args(args)
        try:
            result = await self.connection.execute(query, args)
            return result.rowcount
        except Error:
            return 0

    async def set_user_language(self, user_id: int, language: str):
        await self.apply("""UPDATE users SET lang = %s WHERE id = %s""", (language, user_id))

    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's language
        :param user_id: Telegram ID of the user
        :return: User's language
        """
        return (await self.get("""SELECT lang FROM users WHERE id=%s""", user_id)).get('lang', self.default_language)

    async def get_user_data(self, user_id: int) -> Union[Dict[str, Any], bool]:
        """
        Get user data
        :param user_id: Telegram ID of the user
        :return: Decoded JSON user data
        """
        try:
            return json.loads((await self.get("""SELECT data FROM users WHERE id=%s""", user_id)).get('data', '{}'))
        except TypeError:
            return False

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

        await self.apply("""UPDATE users SET data = %s WHERE id = %s""", (json.dumps(user_data), user_id))
        return user_data

    async def check_user_exists(self, user_id: int) -> bool:
        return bool(await self.check("""SELECT id FROM users WHERE id = %s""", user_id))

    async def create_user(self, user_id: int, language: Optional[str] = None):
        if language is None:
            language = self.default_language

        await self.apply("""INSERT INTO users (id, lang) VALUES (%s, %s)""", (user_id, language))
