from typing import Union, Optional, Dict, Any, List, Tuple, AsyncGenerator
import asyncpg
import os

try:
    import ujson as json
except ImportError:
    import json

from ..base_storage import BaseStorage
from ...logger import LOGGER


class PGStorage(BaseStorage):
    def __init__(self, database: str, host: str = 'localhost', port: Union[str, int] = 5432,
                 user: str = 'postgres', password: Optional[str] = None, default_language: str = 'en'):
        self.database: str = database
        self.host: str = host
        self.port: Union[str, int] = port
        self.user: str = user
        self.password: Optional[str] = password

        self.pool: Optional[asyncpg.pool.Pool] = None

        super().__init__(default_language=default_language)

    async def acquire_pool(self) -> None:
        try:
            self.pool = await asyncpg.pool.create_pool(database=self.database, host=self.host, port=self.port,
                                                       user=self.user, password=self.password)
        except OSError:
            LOGGER.exception('PostgreSQL pool creation failed. *neko things')
        async with self.pool.acquire() as connection:
            with open(os.path.abspath(__file__).replace('pg.py', 'tables.sql'), 'r', encoding='utf-8') as file:
                await connection.execute(file.read())
        LOGGER.info('PostgreSQL pool created successfully. *neko things')

    async def close_pool(self) -> None:
        try:
            await self.pool.expire_connections()
            await self.pool.close()
        except AttributeError:
            LOGGER.exception(f'Attempting to close not acquired PostgreSQL pool. *neko things')
        except Exception:
            LOGGER.exception('PostgreSQL pool closure failed. *neko things')

    async def apply(self, query: str, args: Union[Tuple[Any, ...], Any] = (), ignore_errors: bool = False) -> int:
        """
        Executes SQL query and returns the number of affected rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :param ignore_errors: Whether to ignore errors (recommended for internal usage only).
        :return: Number of affected rows.
        """
        async with self.pool.acquire() as connection:
            try:
                result = await connection.execute(query, *args)
            except Exception as e:
                if not ignore_errors:
                    LOGGER.exception(e)
                return 0
        return int(result.split(' ')[-1])

    async def select(self, query: str, args: Union[Tuple[Any, ...], Any] = ()) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generator that yields rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :return: Yields rows one by one.
        """
        async with self.pool.acquire() as connection:
            try:
                for record in await connection.fetch(query, *args):
                    yield dict(record)
            except Exception as e:
                LOGGER.exception(e)

    async def get(self, query: str, args: Union[Tuple[Any, ...], Any] = (), fetch_all: bool = False)\
            -> Union[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get a single row or a list of rows from the database.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :param fetch_all: Set True if you need a list of rows instead of just a single row.
        :return: A row or a list or rows.
        """
        async with self.pool.acquire() as connection:
            try:
                records = [dict(record) for record in await connection.fetch(query, *args)]
            except Exception as e:
                LOGGER.exception(e)
                return False
        if fetch_all:
            return records
        return records[0] if len(records) else dict()

    async def check(self, query: str, args: Union[Tuple[Any, ...], Any] = ()) -> int:
        return await self.apply(query, args)

    async def set_user_language(self, user_id: int, language: str) -> None:
        """
        Get user's language.
        :param user_id: Telegram ID of the user.
        :param language: User's language to be set.
        :return: None.
        """
        await super().set_user_language(user_id=user_id, language=language)
        await self.apply('UPDATE "nekogram_users" SET "lang" = $1 WHERE "id" = $2;', (language, user_id))

    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's language.
        :param user_id: Telegram ID of the user.
        :return: User's language.
        """
        lang = await self.get_cached_user_language(user_id=user_id)
        if lang is None:
            user = await self.get('SELECT "lang" FROM "nekogram_users" WHERE "id" = $1;', (user_id, ))
            lang = user.get('lang', self.default_language)
        await super().set_user_language(user_id=user_id, language=lang)
        return lang

    async def get_user_data(self, user_id: int, **kwargs) -> Union[Dict[str, Any], bool]:
        """
        Get user data.
        :param user_id: Telegram ID of the user.
        :return: Decoded JSON user data.
        """
        user = await self.get('SELECT "data" FROM "nekogram_users" WHERE "id" = $1;', (user_id, ))
        return json.loads(user.get('data', '{}'))

    async def set_user_data(self, user_id: int, data: Optional[Dict[str, Any]] = None, replace: bool = False, **kwargs)\
            -> Dict[str, Any]:
        """
        Set user data.
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

        await self.apply('UPDATE "nekogram_users" SET "data" = $1 WHERE "id" = $2;', (json.dumps(user_data), user_id))
        return user_data

    async def check_user_exists(self, user_id: int) -> bool:
        return bool(await self.check('SELECT "id" FROM "nekogram_users" WHERE "id" = $1;', (user_id, )))

    async def set_last_message_id(self, user_id: int, message_id: int) -> None:
        await self.apply('UPDATE "nekogram_users" SET "last_message_id" = $1 WHERE "id" = $2;', (message_id, user_id))

    async def get_last_message_id(self, user_id: int) -> Optional[int]:
        user = await self.get('SELECT "last_message_id" FROM "nekogram_users" WHERE "id" = $1;', (user_id, ))
        return user.get('last_message_id')

    async def create_user(self, user_id: int, name: str, username: Optional[str], language: Optional[str] = None) \
            -> None:
        if language is None:
            language = self.default_language
        await self.apply(
            'INSERT INTO "nekogram_users" ("id", "lang", "full_name", "username") VALUES ($1, $2, $3, $4)',
            (user_id, language, name, username)
        )


class KittyPGStorage(PGStorage):
    def __init__(self, database: str, host: str = 'localhost', port: Union[str, int] = 5432,
                 user: str = 'postgres', password: Optional[str] = None, default_language: str = 'en'):
        PGStorage.__init__(self, database=database, host=host, port=port, user=user, password=password,
                           default_language=default_language)

    async def get_user_data(self, user_id: int, bot_token: Optional[str] = None) -> Union[Dict[str, Any], bool]:
        """
        Get user data.
        :param user_id: Telegram ID of the user.
        :param bot_token: Token of the current bot.
        :return: Decoded JSON user data.
        """
        user = await self.get('SELECT "data" FROM "nekogram_users" WHERE "id" = $1;', (user_id, ))
        return json.loads(user['data']).get(bot_token, {})

    async def set_user_data(self, user_id: int, data: Optional[Dict[str, Any]] = None, replace: bool = False,
                            bot_token: Optional[str] = None) -> Dict[str, Any]:
        user = await self.get('SELECT "data" FROM "nekogram_users" WHERE "id" = $1;', (user_id, ))
        user_data = json.loads(user['data'])
        if data is None:
            user_data.pop(bot_token, None)
        else:
            if bot_token not in user_data.keys():
                user_data[bot_token] = data
            else:
                user_data[bot_token].update(data)
        await self.apply('UPDATE "nekogram_users" SET "data" = $1 WHERE "id" = $2;', (json.dumps(user_data), user_id))
        return user_data.get(bot_token, dict())

    async def set_user_menu(self, user_id: int, menu: Optional[str] = None, bot_token: Optional[str] = None) -> str:
        await self.set_user_data(user_id=user_id, data={'menu': menu}, bot_token=bot_token)
        return menu

    async def get_user_menu(self, user_id: int, bot_token: Optional[str] = None) -> Optional[str]:
        data = await self.get_user_data(user_id=user_id, bot_token=bot_token)
        return data.get('menu')
