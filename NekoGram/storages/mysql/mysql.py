from typing import Optional, Union, Any, AsyncGenerator, List, Dict, Tuple
from pymysql import err as mysql_errors
from ..base_storage import BaseStorage
from ...logger import LOGGER
from pymysql.constants import CLIENT
from contextlib import suppress
import aiomysql

try:
    from aiomysql.cursors import DictCursor
except ImportError:
    raise ImportError('Install aiomysql to use MySQLStorage!')

try:
    import ujson as json
except ImportError:
    import json


class MySQLStorage(BaseStorage):
    def __init__(self, database: str, host: str = 'localhost', port: int = 3306, user: str = 'root',
                 password: Optional[str] = None, default_language: str = 'en'):
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
        with open('NekoGram/storages/mysql/tables.json', 'r') as f:
            self._table_structs: Dict[str, Dict[str, Dict[str, Optional[str]]]] = json.load(f)
        super().__init__(default_language=default_language)

    def __del__(self):
        self.pool.close()

    async def verify_table(self, table: str, required_by: str):
        r = await self.get(f'DESCRIBE {table}', fetch_all=True)
        structure = self._table_structs[table]
        if isinstance(r, list):  # Table exists
            r: Dict[str, Dict[str, Optional[str]]] = {x['Field']: x for x in r}
            table_struct: Dict[str, Dict[str, Optional[str]]] = {x['Field']: x for x in structure.values()}
            for key, value in table_struct.items():
                sql_code = value['struct']
                value.pop('struct')
                if not r.get(key):  # Field does not exist
                    await self.apply(f'ALTER TABLE {table} ADD {sql_code}')
                    LOGGER.warning(f'Added {key} to {table} required by {required_by}.')
                elif r[key] != value:  # Field is defined in a wrong way
                    await self.apply(f'ALTER TABLE {table} MODIFY {sql_code}')
                    LOGGER.warning(f'Altered {key} in {table} required by {required_by}.')

        else:  # Table does not exist
            LOGGER.warning(f'Table {table} required by {required_by} does not exist, creating..')
            await self.apply(f'CREATE TABLE {table} ({",".join([f["struct"] for f in structure.values()])}) '
                             f'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;')

    async def add_tables(self, structure: Dict[str, Dict[str, Dict[str, Optional[str]]]], required_by: str):
        self._table_structs.update(structure)
        for table in structure.keys():
            await self.verify_table(table=table, required_by=required_by)

    async def _verify(self):
        connection = await aiomysql.connect(host=self.host, user=self.user, password=self.password, port=self.port,
                                            client_flag=CLIENT.MULTI_STATEMENTS)
        async with connection.cursor(DictCursor) as cursor:
            await cursor.execute('SHOW DATABASES LIKE %s', self.database)
            if not await cursor.fetchone():
                LOGGER.warning(f'MySQL database {self.database} does not exist, creating..')
                await cursor.execute(f'CREATE DATABASE IF NOT EXISTS {self.database} DEFAULT CHARACTER SET '
                                     f'utf8mb4 COLLATE utf8mb4_unicode_ci')
                await connection.commit()
        connection.close()

    async def acquire_pool(self):
        """
        Creates a new MySQL pool
        """
        LOGGER.info('Verifying database existence..')
        await self._verify()
        if isinstance(self.pool, aiomysql.Pool):
            with suppress(Exception):
                self.pool.close()

        self.pool = await aiomysql.create_pool(host=self.host, port=self.port, user=self.user,
                                               password=self.password, db=self.database)
        LOGGER.info('Verifying table structures, hold tight..')
        await self.verify_table(table='nekogram_users', required_by='NekoGram')
        LOGGER.info('MySQLStorage initialized successfully. ~nya')

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
                except mysql_errors.Error as e:
                    print(e)
                    await conn.rollback()

                if 'insert into' in query.lower():
                    return cursor.lastrowid
                else:
                    return cursor.rowcount

    async def select(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> \
            AsyncGenerator[Dict[str, Any], None]:
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
                    await conn.commit()
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
                    await conn.commit()

                    if fetch_all:
                        return await cursor.fetchall()
                    else:
                        result = await cursor.fetchone()
                        return result if result else dict()
                except mysql_errors.Error:
                    return False

    async def check(self, query: str, args: Optional[Union[Tuple[Any, ...], Dict[str, Any], Any]] = None) -> int:
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)
                    await conn.commit()

                    return cursor.rowcount
                except mysql_errors.Error:
                    return 0

    async def set_user_language(self, user_id: int, language: str):
        await super().set_user_language(user_id=user_id, language=language)
        await self.apply('UPDATE nekogram_users SET lang = %s WHERE id = %s', (language, user_id))

    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's language
        :param user_id: Telegram ID of the user
        :return: User's language
        """
        lang = await self.get_cached_user_language(user_id=user_id)
        if lang is None:
            lang = (await self.get('SELECT lang FROM nekogram_users WHERE id=%s',
                                   user_id)).get('lang', self.default_language)
        await super().set_user_language(user_id=user_id, language=lang)
        return lang

    async def get_user_data(self, user_id: int) -> Union[Dict[str, Any], bool]:
        """
        Get user data
        :param user_id: Telegram ID of the user
        :return: Decoded JSON user data
        """
        try:
            return json.loads((await self.get('SELECT data FROM nekogram_users WHERE id=%s',
                                              user_id)).get('data', '{}'))
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

        await self.apply('UPDATE nekogram_users SET data = %s WHERE id = %s', (json.dumps(user_data), user_id))
        return user_data

    async def set_user_menu(self, user_id: int, menu: Optional[str] = None):
        await self.set_user_data(user_id=user_id, data={'menu': menu})
        return menu

    async def get_user_menu(self, user_id: int) -> Optional[str]:
        return (await self.get_user_data(user_id=user_id)).get('menu')

    async def check_user_exists(self, user_id: int) -> bool:
        return bool(await self.check('SELECT id FROM nekogram_users WHERE id = %s', user_id))

    async def set_last_message_id(self, user_id: int, message_id: int):
        await self.apply('UPDATE nekogram_users SET last_message_id = %s WHERE id = %s', (message_id, user_id))

    async def get_last_message_id(self, user_id: int) -> Optional[int]:
        return (await self.get('SELECT last_message_id FROM nekogram_users WHERE id = %s',
                               user_id)).get('last_message_id')

    async def create_user(self, user_id: int, language: Optional[str] = None):
        if language is None:
            language = self.default_language

        await self.apply('INSERT INTO nekogram_users (id, lang) VALUES (%s, %s)', (user_id, language))
