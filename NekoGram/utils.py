from aiogram.dispatcher.middlewares import BaseMiddleware
from .base_neko import BaseNeko
from aiogram import types
from typing import Union
from io import BytesIO
import aiohttp
try:
    import ujson as json
except ImportError:
    import json


class HandlerInjector(BaseMiddleware):
    """
    Neko injector middleware
    """

    def __init__(self, neko: BaseNeko):
        super().__init__()
        self.neko: BaseNeko = neko

    async def on_process_message(self, message: types.Message, _: dict):
        """
        This handler is called when dispatcher receives a message
        """
        # Get current handler
        message.conf['neko'] = self.neko

    async def on_process_callback_query(self, call: types.CallbackQuery, _: dict):
        """
        This handler is called when dispatcher receives a call
        """
        # Get current handler
        call.conf['neko'] = self.neko
        call.message.conf['neko'] = self.neko
        call.message.from_user = call.from_user


async def telegraph_upload(f: BytesIO, mime: str = 'image/png') -> Union[str, bool]:
    """
    Upload a file to Telegra.ph
    :param f: File BytesIO
    :param mime: File MIME type
    :return: File URL on success
    """
    # f = await (max(message.photo, key=lambda c: c.width)).download(destination=BytesIO())
    data = aiohttp.FormData()
    data.add_field('file', f.read(), filename=f'file.{mime.split("/")[1]}', content_type=mime)
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),
                                         json_serialize=json.dumps) as session:
            async with session.post(url='https://telegra.ph/upload', data=data) as r:
                r = await r.json()
                if isinstance(r, dict) and r.get('error'):
                    return False
                if not r[-1]["src"].startswith('/'):
                    r[-1]["src"] = '/' + r[-1]["src"]
                return f'https://telegra.ph{r[-1]["src"]}'
    except aiohttp.ClientError:
        return False
