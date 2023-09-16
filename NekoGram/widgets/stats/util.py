from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram import types
import os

try:
    import ujson as json
except ImportError:
    import json

from ...base_neko import BaseNeko


class StatsInjector(BaseMiddleware):
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
        interaction_data = json.dumps({
            'type': 'message', 'bot_token': message.conf['parent']().conf.get('request_token')
        })
        await self.neko.storage.apply(
            'INSERT INTO nekogram_stats (user_id, interaction_date, interaction) VALUES (%s, CURRENT_TIMESTAMP(), %s)',
            (message.from_user.id, interaction_data),
            ignore_errors=True
        )

    async def on_process_callback_query(self, call: types.CallbackQuery, _: dict):
        """
        This handler is called when dispatcher receives a callback query
        """
        interaction_data = json.dumps({
            'type': 'call', 'bot_token': call.conf['parent']().conf.get('request_token')
        })
        await self.neko.storage.apply(
            'INSERT INTO nekogram_stats (user_id, interaction_date, interaction) VALUES (%s, CURRENT_TIMESTAMP(), %s)',
            (call.from_user.id, interaction_data),
            ignore_errors=True
        )

    async def on_process_inline_query(self, query: types.InlineQuery, _: dict):
        """
        This handler is called when dispatcher receives an inline query
        """
        interaction_data = json.dumps({
            'type': 'query', 'bot_token': query.conf['parent']().conf.get('request_token')
        })
        await self.neko.storage.apply(
            'INSERT INTO nekogram_stats (user_id, interaction_date, interaction) VALUES (%s, CURRENT_TIMESTAMP(), %s)',
            (query.from_user.id, interaction_data),
            ignore_errors=True
        )


async def startup(neko: BaseNeko):
    sql_path = os.path.abspath(__file__).rstrip('util.py')
    with open(os.path.join(f'{sql_path}sql', 'tables.json'), 'r') as f:
        structure = json.load(f)
    await neko.storage.add_tables(structure, required_by='stats')
    neko.dp.middleware.setup(StatsInjector(neko))
