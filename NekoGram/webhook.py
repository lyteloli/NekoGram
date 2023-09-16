from aiogram.dispatcher.webhook import WebhookRequestHandler, web
from aiogram.utils.executor import Executor

from .base_neko import BaseNeko


class KittyExecutor(Executor):
    def __init__(self, neko: BaseNeko, skip_updates=None, check_ip=False, retry_after=None, loop=None):
        super().__init__(
            dispatcher=neko.dp, skip_updates=skip_updates, check_ip=check_ip, retry_after=retry_after, loop=loop
        )
        self.neko: BaseNeko = neko


class KittyWebhook(WebhookRequestHandler):
    async def post(self):
        self.validate_ip()
        neko: BaseNeko = self.request.app['APP_EXECUTOR'].neko

        dispatcher = self.get_dispatcher()
        update = await self.parse_update(dispatcher.bot)
        update.conf['neko'] = neko
        update.conf['request_token'] = self.request.match_info['token']

        with neko.bot.with_token(update.conf['request_token']):
            results = await self.process_update(update)
        response = self.get_response(results)

        if response:
            web_response = response.get_web_response()
        else:
            web_response = web.Response(text='ok')

        if self.request.app.get('RETRY_AFTER', None):
            web_response.headers['Retry-After'] = self.request.app['RETRY_AFTER']

        return web_response
