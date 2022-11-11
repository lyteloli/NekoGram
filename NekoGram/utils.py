from aiogram.dispatcher.middlewares import BaseMiddleware
from .base_neko import BaseNeko
from aiogram import types


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
