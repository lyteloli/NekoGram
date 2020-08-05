from typing import Optional, Union, Any, AsyncIterable, List, Dict, Tuple
from ..base_storage import BaseStorage
from aiomysql.cursors import DictCursor
from pymysql import err as mysql_errors
from contextlib import suppress
import aiomysql
import asyncio

try:
    import ujson as json
except ImportError:
    import json


class MySQLStorage(BaseStorage):
    def __init__(self, database: str, host: str = 'localhost', port: int = 3306, user: str = 'root',
                 password: Optional[str] = None):
        """
        Initialize database
        :param database: Database name
        :param host: Database host
        :param port: Database port
        :param user: Database user
        :param password: Database password
        """
        self.pool: Optional[aiomysql.Pool] = None
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.password: str = password
        self.database = database

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.acquire_pool())
        super().__init__()

    def __del__(self):
        self.pool.close()

    async def acquire_pool(self):
        """
        Creates a new MySQL pool
        """
        if isinstance(self.pool, aiomysql.Pool):
            with suppress(Exception):
                self.pool.close()

        self.pool = await aiomysql.create_pool(host=self.host, port=self.port, user=self.user,
                                               password=self.password, db=self.database)

    @staticmethod
    def _verify_args(args: Optional[Union[Tuple[Union[Any, Dict[str, Any]], ...], Any]]):
        if args is None:
            args = tuple()
        if not isinstance(args, (tuple, dict)):
            args = (args,)
        return args

    async def apply(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> int:
        """
        Executes SQL query and returns the number of affected rows
        :param query: SQL query to execute
        :param args: Arguments passed to the SQL query
        :return: Number of affected rows
        """
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)
                    await conn.commit()
                except mysql_errors.Error:
                    await conn.rollback()

                if 'insert into' in query.lower():
                    return cursor.lastrowid
                else:
                    return cursor.rowcount

    async def select(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> \
            AsyncIterable[Dict[str, Any]]:
        """
        Generator that yields rows
        :param query: SQL query to execute
        :param args: Arguments passed to the SQL query
        :return: Yields rows one by one
        """
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)
                    while True:
                        item = await cursor.fetchone()
                        if item:
                            yield item
                        else:
                            break
                except mysql_errors.Error:
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
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)

                    if fetch_all:
                        return await cursor.fetchall()
                    else:
                        return await cursor.fetchone()
                except mysql_errors.Error:
                    return False

    async def check(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> int:
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)

                    return cursor.rowcount
                except mysql_errors.Error:
                    return 0

    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's language
        :param user_id: Telegram ID of the user
        :return: User's language
        """
        return (await self.get("""SELECT lang FROM users WHERE id=%s""", user_id))['lang']

    async def get_user_data(self, user_id: int) -> Union[Dict[str, Any], bool]:
        """
        Get user data
        :param user_id: Telegram ID of the user
        :return: Decoded JSON user data
        """
        try:
            return json.loads((await self.get("""SELECT data FROM users WHERE id=%s""", user_id))['data'])
        except TypeError:
            return False

    async def set_user_data(self, user_id: int, data: Optional[Dict[str, Any]] = None,
                            replace: bool = False) -> Dict[str, Any]:
        if data is None:
            new_data = dict()
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

    async def create_user(self, user_id: int, language: str):
        await self.apply("""INSERT INTO users (id, lang) VALUES (%s, %s)""", (user_id, language))
