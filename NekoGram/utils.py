from aiogram.dispatcher.middlewares import BaseMiddleware
from contextlib import suppress
from aiogram import types
from typing import Union
from io import BytesIO
import aiohttp

try:
    import ujson as json
except ImportError:
    import json

from .base_neko import BaseNeko


class HandlerInjector(BaseMiddleware):
    """
    Neko injector middleware.
    """

    def __init__(self, neko: BaseNeko):
        super().__init__()
        self.neko: BaseNeko = neko

    async def _actualize(self, user: types.User) -> None:
        await self.neko.storage.apply(
            f'UPDATE nekogram_users SET '
            f'full_name = {self.neko.storage.p(1)}, '
            f'username = {self.neko.storage.p(2)} '
            f'WHERE id = {self.neko.storage.p(3)}',
            (user.full_name, user.username, user.id)
        )

    async def on_pre_process_message(self, message: types.Message, _: dict):
        """
        This handler is called when dispatcher receives a message.
        """
        # Get current handler
        message.conf['neko'] = self.neko
        await self._actualize(message.from_user)
        with suppress(Exception):
            message.conf['request_token'] = message.conf['parent']().conf['request_token']

    async def on_process_callback_query(self, call: types.CallbackQuery, _: dict):
        """
        This handler is called when dispatcher receives a callback query.
        """
        # Get current handler
        call.conf['neko'] = self.neko
        call.message.conf['neko'] = self.neko
        call.message.from_user = call.from_user
        await self._actualize(call.from_user)
        with suppress(Exception):
            call.conf['request_token'] = call.conf['parent']().conf['request_token']

    async def on_process_inline_query(self, query: types.InlineQuery, _: dict):
        """
        This handler is called when dispatcher receives an inline query.
        """
        # Get current handler
        query.conf['neko'] = self.neko
        await self._actualize(query.from_user)
        with suppress(Exception):
            query.conf['request_token'] = query.conf['parent']().conf['request_token']


async def telegraph_upload(f: Union[BytesIO, types.Message], mime: str = 'image/png') -> Union[str, bool]:
    """
    Upload a file to https://telegra.ph.
    :param f: A BytesIO file or an AIOGram message object.
    :param mime: File MIME type.
    :return: File URL on success.
    """
    if isinstance(f, types.Message):
        if f.text:
            raise ValueError('You message does not seem to have any media')
        f = f.photo[-1] if f.photo else getattr(f, f.content_type)
        f = f.download(destination=BytesIO())

    data = aiohttp.FormData()
    data.add_field('file', f.read(), filename=f'file.{mime.split("/")[1]}', content_type=mime)
    try:
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False), json_serialize=json.dumps
        ) as session:
            async with session.post(url='https://telegra.ph/upload', data=data) as r:
                r = await r.json()
                if isinstance(r, dict) and r.get('error'):
                    return False
                item_path: str = r[-1]['src']
                if not item_path.startswith('/'):
                    item_path = f'/{item_path}'
                return f'https://telegra.ph{item_path}'
    except aiohttp.ClientError:
        return False


class NekoGramWarning(Warning):
    ...
