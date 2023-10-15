from typing import Union, Optional, Dict, Any, List, Tuple, AsyncGenerator
from contextlib import suppress
import os

try:
    import aiosqlite
except ImportError:
    raise ImportError('Install `aiosqlite` to use `SQLiteStorage`!')

try:
    import ujson as json
except ImportError:
    import json

from ..base_storage import BaseStorage
from ...logger import LOGGER


class SQLiteStorage(BaseStorage):
    def __init__(self, database: str = ':memory:', default_language: str = 'en'):
        self.database: str = database

        self.pool: Optional[aiosqlite.Connection] = None

        super().__init__(default_language=default_language)

    @property
    def p(self, counter: Optional[int] = None) -> str:
        return '?'

    async def acquire_pool(self) -> bool:
        """
        Creates a new SQLite pool.
        :return: True if the pool was successfully created, otherwise False.
        """
        try:
            self.pool = await aiosqlite.connect(database=self.database)
            self.pool.row_factory = aiosqlite.Row
        except Exception:  # noqa
            LOGGER.exception('SQLite pool creation failed. *neko things')
            return False
        with open(os.path.abspath(__file__).replace('sqlite.py', 'tables.sql'), 'r', encoding='utf-8') as file:
            await self.pool.execute(file.read())
            await self.pool.commit()
        LOGGER.info('SQLite pool created successfully. *neko things')
        return True

    async def close_pool(self) -> bool:
        """
        Closes existing SQLite pool.
        :return: True if the pool was successfully closed, otherwise False.
        """
        with suppress(Exception):
            await self.pool.close()
            return True
        LOGGER.exception('SQLite pool closure failed. *neko things')
        return False

    async def apply(self, query: str, args: Union[Tuple[Any, ...], Any] = (), ignore_errors: bool = False) -> int:
        """
        Executes SQL query and returns the number of affected rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :param ignore_errors: Whether to ignore errors (recommended for internal usage only).
        :return: Number of affected rows.
        """
        try:
            cursor: aiosqlite.Cursor = await self.pool.execute(query, self._verify_args(args))
            await self.pool.commit()
        except Exception as e:
            if not ignore_errors:
                LOGGER.exception(e)
            return 0
        return cursor.rowcount

    async def select(self, query: str, args: Union[Tuple[Any, ...], Any] = ()) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generator that yields rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :return: Yields rows one by one.
        """
        try:
            cursor: aiosqlite.Cursor = await self.pool.execute(query, self._verify_args(args))
            while True:
                item = await cursor.fetchone()
                if item:
                    yield self._AttrDict(item)
                else:
                    break
        except Exception:  # noqa
            pass

    async def get(
            self,
            query: str,
            args: Union[Tuple[Any, ...], Any] = (),
            fetch_all: bool = False,
            use_attr_dict: bool = True
    ) -> Union[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get a single row or a list of rows from the database.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :param fetch_all: Set True if you need a list of rows instead of just a single row.
        :param use_attr_dict: Whether to use dict or AttrDict for fetched rows, is relevant with fetch_all=True only.
        :return: A row or a list or rows.
        """
        try:
            cursor: aiosqlite.Cursor = await self.pool.execute(query, self._verify_args(args))
        except Exception as e:
            LOGGER.exception(e)
            return False
        if fetch_all:
            if use_attr_dict:
                return [self._AttrDict(row) for row in await cursor.fetchall()]
            return [dict(row) for row in await cursor.fetchall()]
        result: aiosqlite.Row = await cursor.fetchone()
        return self._AttrDict(result) if result else {}

    async def check(self, query: str, args: Union[Tuple[Any, ...], Dict[str, Any], Any] = ()) -> int:
        """
        Executes SQL query and returns the number of affected rows.
        :param query: SQL query to execute.
        :param args: Arguments passed to the SQL query.
        :return: Number of affected rows.
        """
        try:
            cursor: aiosqlite.Cursor = await self.pool.execute(query, self._verify_args(args))
        except Exception:  # noqa
            return 0
        return len(await cursor.fetchall())

    async def set_user_language(self, user_id: int, language: str) -> None:
        """
        Get user's language.
        :param user_id: Telegram ID of the user.
        :param language: User's language to be set.
        :return: None.
        """
        await super().set_user_language(user_id=user_id, language=language)
        await self.apply('UPDATE "nekogram_users" SET "lang" = ? WHERE "id" = ?;', (language, user_id))

    async def get_user_language(self, user_id: int) -> str:
        """
        Get user's language.
        :param user_id: Telegram ID of the user.
        :return: User's language.
        """
        lang = await self.get_cached_user_language(user_id=user_id)
        if lang is None:
            user = await self.get('SELECT "lang" FROM "nekogram_users" WHERE "id" = ?;', (user_id, ))
            lang = user.get('lang', self.default_language)
        await super().set_user_language(user_id=user_id, language=lang)
        return lang

    async def get_user_data(self, user_id: int, **kwargs) -> Union[Dict[str, Any], bool]:
        """
        Get user data.
        :param user_id: Telegram ID of the user.
        :return: Decoded JSON user data.
        """
        user = await self.get('SELECT "data" FROM "nekogram_users" WHERE "id" = ?;', (user_id, ))
        return json.loads(user.get('data', '{}'))

    async def set_user_data(
            self,
            user_id: int,
            data: Optional[Dict[str, Any]] = None,
            replace: bool = False,
            **kwargs
    ) -> Dict[str, Any]:
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

        await self.apply('UPDATE "nekogram_users" SET "data" = ? WHERE "id" = ?;', (json.dumps(user_data), user_id))
        return user_data

    async def check_user_exists(self, user_id: int) -> bool:
        """
        Check that user exists in the database.
        :param user_id: Telegram ID of the user.
        :return: boolean value.
        """
        return bool(await self.check('SELECT "id" FROM "nekogram_users" WHERE "id" = ?;', (user_id, )))

    async def set_last_message_id(self, user_id: int, message_id: int) -> None:
        """
        Set last message ID.
        :param user_id: Telegram ID of the user.
        :param message_id: Telegram ID of the message.
        :return: None.
        """
        await self.apply('UPDATE "nekogram_users" SET "last_message_id" = ? WHERE "id" = ?;', (message_id, user_id))

    async def get_last_message_id(self, user_id: int) -> Optional[int]:
        """
        Set last message ID.
        :param user_id: Telegram ID of the user.
        :return: Telegram ID of the message if was set, otherwise None.
        """
        user = await self.get('SELECT "last_message_id" FROM "nekogram_users" WHERE "id" = ?;', (user_id, ))
        return user.get('last_message_id')

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
            'INSERT INTO "nekogram_users" ("id", "lang", "full_name", "username") VALUES (?, ?, ?, ?)',
            (user_id, language, name, username)
        )


class KittySQLiteStorage(SQLiteStorage):
    def __init__(self, database: str, default_language: str = 'en'):
        SQLiteStorage.__init__(self, database=database, default_language=default_language)

    async def get_user_data(self, user_id: int, bot_token: Optional[str] = None) -> Union[Dict[str, Any], bool]:
        """
        Get user data.
        :param user_id: Telegram ID of the user.
        :param bot_token: Token of the current bot.
        :return: Decoded JSON user data.
        """
        user = await self.get('SELECT "data" FROM "nekogram_users" WHERE "id" = ?;', (user_id, ))
        return json.loads(user['data']).get(bot_token, {})

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
        user = await self.get('SELECT "data" FROM "nekogram_users" WHERE "id" = ?;', (user_id, ))
        user_data = json.loads(user['data'])
        if data is None:
            user_data.pop(bot_token, None)
        else:
            if bot_token not in user_data.keys() or replace:
                user_data[bot_token] = data
            else:
                user_data[bot_token].update(data)
        await self.apply('UPDATE "nekogram_users" SET "data" = ? WHERE "id" = ?;', (json.dumps(user_data), user_id))
        return user_data.get(bot_token, {})

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
        data = await self.get_user_data(user_id=user_id, bot_token=bot_token)
        return data.get('menu')
