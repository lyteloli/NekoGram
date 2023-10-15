from typing import Optional, Union, Any, AsyncGenerator, List, Dict, Tuple
from pymysql import err as mysql_errors
from pymysql.constants import CLIENT
from contextlib import suppress
import aiomysql
import os

try:
    from aiomysql.cursors import DictCursor
except ImportError:
    raise ImportError('Install `aiomysql` to use `MySQLStorage`!')

try:
    import ujson as json
except ImportError:
    import json

from ..base_storage import BaseStorage
from ...logger import LOGGER


class MySQLStorage(BaseStorage):
    def __init__(
            self,
            database: str,
            host: str = 'localhost',
            port: int = 3306,
            user: str = 'root',
            password: Optional[str] = None,
            default_language: str = 'en'
    ):
        """
        Initialize database.
        :param database: Database name.
        :param host: Database host.
        :param port: Database port.
        :param user: Database user.
        :param password: Database password.
        """

        self.pool: Optional[aiomysql.Pool] = None
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.password: str = password
        self.database = database

        with open(os.path.abspath(__file__).replace('mysql.py', 'tables.json'), 'r', encoding='utf-8') as file:
            self._table_structs: Dict[str, Dict[str, Dict[str, Optional[str]]]] = json.load(file)
        super().__init__(default_language=default_language)

    def p(self, counter: Optional[int] = None) -> str:
        return '%s'

    def __del__(self):
        self.pool.close()

    async def verify_table(self, table: str, required_by: str) -> None:
        r = await self.get(f'DESCRIBE {table}', fetch_all=True)
        structure = self._table_structs[table]
        if isinstance(r, list):  # Table exists
            r: Dict[str, Dict[str, Optional[str]]] = {x['Field']: x for x in r}
            table_struct: Dict[str, Dict[str, Optional[str]]] = {
                x['Field']: x for x in structure.values() if not isinstance(x, list)
            }
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
            fields = ','.join([f['struct'] for f in structure.values() if not isinstance(f, list)])
            await self.apply(
                f'CREATE TABLE {table} ({fields}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;'
            )

        if structure.get('_extras'):
            for i in structure['_extras']:
                await self.apply(i, ignore_errors=True)

    async def add_tables(self, structure: Dict[str, Dict[str, Dict[str, Optional[str]]]], required_by: str) -> None:
        self._table_structs.update(structure)
        for table in structure.keys():
            await self.verify_table(table=table, required_by=required_by)

    async def _verify(self) -> None:
        connection = await aiomysql.connect(
            host=self.host, user=self.user, password=self.password, port=self.port, client_flag=CLIENT.MULTI_STATEMENTS
        )
        async with connection.cursor(DictCursor) as cursor:
            await cursor.execute('SHOW DATABASES LIKE %s', self.database)
            if not await cursor.fetchone():
                LOGGER.warning(f'MySQL database {self.database} does not exist, creating..')
                await cursor.execute(
                    f'CREATE DATABASE IF NOT EXISTS {self.database} DEFAULT CHARACTER '
                    f'SET utf8mb4 COLLATE utf8mb4_unicode_ci'
                )
                await connection.commit()
        connection.close()

    async def acquire_pool(self) -> bool:
        """
        Creates a new MySQL pool.
        """
        LOGGER.info('Verifying database existence..')
        await self._verify()
        if isinstance(self.pool, aiomysql.Pool):
            with suppress(Exception):
                self.pool.close()

        self.pool = await aiomysql.create_pool(
            host=self.host, port=self.port, user=self.user, password=self.password, db=self.database
        )
        LOGGER.info('Verifying table structures, hold tight..')
        await self.verify_table(table='nekogram_users', required_by='NekoGram')
        LOGGER.info('MySQLStorage initialized successfully. ~nya')
        return True

    async def close_pool(self) -> bool:
        """
        Closes existing MySQL pool.
        :return: True if the pool was successfully closed, otherwise False.
        """
        with suppress(Exception):
            self.pool.close()
            return True
        return False

    async def apply(
            self,
            query: str,
            args: Union[Tuple[Any, ...], Dict[str, Any], Any] = (),
            ignore_errors: bool = False
    ) -> int:
        """
        Executes SQL query and returns the number of affected rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :param ignore_errors: Whether to ignore errors (recommended for internal usage only).
        :return: Number of affected rows.
        """
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)
                    await conn.commit()
                except mysql_errors.Error as e:
                    if not ignore_errors:
                        LOGGER.exception(e)
                    await conn.rollback()

                if 'insert into' in query.lower():
                    return cursor.lastrowid
                else:
                    return cursor.rowcount

    async def select(
            self,
            query: str,
            args: Union[Tuple[Any, ...], Dict[str, Any], Any] = ()
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generator that yields rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :return: Yields rows one by one.
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
                            yield self._AttrDict(item)
                        else:
                            break
                except mysql_errors.Error:
                    pass

    async def get(
            self,
            query: str,
            args: Union[Tuple[Any, ...], Dict[str, Any], Any] = (),
            fetch_all: bool = False,
            use_attr_dict: bool = True
    ) -> Union[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get a single row or a list of rows from the database.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :param fetch_all: Set True if you need a list of rows instead of just a single row.
        :param use_attr_dict: Whether to use dict or AttrDict for fetched rows.
        :return: A row or a list of rows.
        """
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)
                    await conn.commit()

                    if fetch_all:
                        if use_attr_dict:
                            return [self._AttrDict(row) for row in await cursor.fetchall()]
                        return await cursor.fetchall() or []
                    else:
                        result = await cursor.fetchone() or dict()
                        if use_attr_dict:
                            return self._AttrDict(result)
                        return result
                except mysql_errors.Error:
                    return False

    async def check(self, query: str, args: Union[Tuple[Any, ...], Dict[str, Any], Any] = ()) -> int:
        """
        Executes SQL query and returns the number of affected rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :return: Number of affected rows.
        """
        args = self._verify_args(args)
        async with self.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                try:
                    await cursor.execute(query, args)
                    await conn.commit()

                    return cursor.rowcount
                except mysql_errors.Error:
                    return 0

    async def set_user_language(self, user_id: int, language: str) -> None:
        """
        Get user's language.
        :param user_id: Telegram ID of the user.
        :param language: User's language to be set.
        :return: None.
        """
        await super().set_user_language(user_id=user_id, language=language)
        await self.apply('UPDATE nekogram_users SET lang = %s WHERE id = %s', (language, user_id))

    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's language.
        :param user_id: Telegram ID of the user.
        :return: User's language.
        """
        lang = await self.get_cached_user_language(user_id=user_id)
        if lang is None:
            lang = (
                await self.get('SELECT lang FROM nekogram_users WHERE id = %s', user_id)
            ).get('lang', self.default_language)
        await super().set_user_language(user_id=user_id, language=lang)
        return lang

    async def get_user_data(self, user_id: int, **kwargs) -> Union[Dict[str, Any], bool]:
        """
        Get user data.
        :param user_id: Telegram ID of the user.
        :return: Decoded JSON user data.
        """
        return json.loads((await self.get('SELECT data FROM nekogram_users WHERE id = %s', user_id))['data'])

    async def set_user_data(
            self,
            user_id: int,
            data: Optional[Dict[str, Any]] = None,
            replace: bool = False,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Set user data
        :param user_id: Telegram ID of the user.
        :param data: User data.
        :param replace: Replace user data with `data` if replace=True, otherwise merge existing with `data`.
        :return: Decoded JSON user data.
        """
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

    async def check_user_exists(self, user_id: int) -> bool:
        """
        Check that user exists in the database.
        :param user_id: Telegram ID of the user.
        :return: boolean value.
        """
        return bool(await self.check('SELECT id FROM nekogram_users WHERE id = %s', user_id))

    async def set_last_message_id(self, user_id: int, message_id: int) -> None:
        """
        Set last message ID.
        :param user_id: Telegram ID of the user.
        :param message_id: Telegram ID of the message.
        :return: None.
        """
        await self.apply('UPDATE nekogram_users SET last_message_id = %s WHERE id = %s', (message_id, user_id))

    async def get_last_message_id(self, user_id: int) -> Optional[int]:
        """
        Set last message ID.
        :param user_id: Telegram ID of the user.
        :return: Telegram ID of the message if was set, otherwise None.
        """
        return (
            await self.get('SELECT last_message_id FROM nekogram_users WHERE id = %s', user_id)
        ).get('last_message_id')

    async def create_user(
            self,
            user_id: int,
            name: str,
            username: Optional[str] = None,
            language: Optional[str] = None
    ) -> None:
        """
        Create user.
        :param user_id: Telegram ID of the user.
        :param name: Telegram first and last name of the user.
        :param username: Telegram username of the user.
        :param language: User's language.
        :return: None.
        """
        if language is None:
            language = self.default_language

        await self.apply(
            'INSERT INTO nekogram_users (id, lang, full_name, username) VALUES (%s, %s, %s, %s)',
            (user_id, language, name, username)
        )


class KittyMySQLStorage(MySQLStorage):
    def __init__(
            self,
            database: str,
            host: str = 'localhost',
            port: int = 3306,
            user: str = 'root',
            password: Optional[str] = None,
            default_language: str = 'en'
    ):
        MySQLStorage.__init__(
            self,
            database=database,
            host=host,
            port=port,
            user=user,
            password=password,
            default_language=default_language
        )

    async def get_user_data(self, user_id: int, bot_token: Optional[str] = None) -> Union[Dict[str, Any], bool]:
        """
        Get user data.
        :param user_id: Telegram ID of the user.
        :param bot_token: Token of the current bot.
        :return: Decoded JSON user data.
        """
        return json.loads(
            (await self.get('SELECT data FROM nekogram_users WHERE id = %s', user_id))['data']
        ).get(bot_token, dict())

    async def set_user_data(
            self,
            user_id: int,
            data: Optional[Dict[str, Any]] = None,
            replace: bool = False,
            bot_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set user data.
        :param user_id: Telegram ID of the user.
        :param data: User data.
        :param replace: Replace user data with `data` if replace=True, otherwise merge existing with `data`.
        :param bot_token: Token of the Telegram bot obtained through @BotFather.
        :return: Decoded JSON user data.
        """
        raw_user_data = json.loads((await self.get('SELECT data FROM nekogram_users WHERE id = %s', user_id))['data'])
        if data is None:
            raw_user_data.pop(bot_token, None)
        else:
            if bot_token not in raw_user_data.keys() or replace:
                raw_user_data[bot_token] = data
            else:
                raw_user_data[bot_token].update(data)

        await self.apply('UPDATE nekogram_users SET data = %s WHERE id = %s', (json.dumps(raw_user_data), user_id))
        return raw_user_data.get(bot_token, dict())

    async def set_user_menu(self, user_id: int, menu: Optional[str] = None, bot_token: Optional[str] = None) -> str:
        """
        Set user menu.
        :param user_id: Telegram ID of the user.
        :param menu: User menu.
        :param bot_token: Token of the Telegram bot obtained through @BotFather.
        :return: User menu.
        """
        await self.set_user_data(user_id=user_id, data={'menu': menu}, bot_token=bot_token)
        return menu

    async def get_user_menu(self, user_id: int, bot_token: Optional[str] = None) -> Optional[str]:
        """
        Set user menu.
        :param user_id: Telegram ID of the user.
        :param bot_token: Token of the Telegram bot obtained through @BotFather.
        :return: User menu if was set, otherwise None.
        """
        return (await self.get_user_data(user_id=user_id, bot_token=bot_token)).get('menu')
