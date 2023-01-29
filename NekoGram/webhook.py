from aiogram.utils.executor import Executor, DEFAULT_ROUTE_NAME, APP_EXECUTOR_KEY, BOT_DISPATCHER_KEY
from aiogram.dispatcher.webhook import WebhookRequestHandler, web
from .base_neko import BaseNeko
import datetime
import functools


class KittyExecutor(Executor):
    def __init__(self, neko: BaseNeko, skip_updates=None, check_ip=False, retry_after=None, loop=None):
        super().__init__(dispatcher=neko.dp, skip_updates=skip_updates, check_ip=check_ip, retry_after=retry_after,
                         loop=loop)
        self.neko: BaseNeko = neko

    # def _prepare_webhook(self, path=None, handler=WebhookRequestHandler, route_name=DEFAULT_ROUTE_NAME, app=None):
    #     self._check_frozen()
    #     self._freeze = True
    #
    #     if app is not None:
    #         self._web_app = app
    #     elif self._web_app is None:
    #         self._web_app = app = web.Application()
    #     else:
    #         raise RuntimeError("web.Application() is already configured!")
    #
    #     app['neko'] = self.neko
    #
    #     if self.retry_after:
    #         app['RETRY_AFTER'] = self.retry_after
    #
    #     if self._identity == app.get(self._identity):
    #         # App is already configured
    #         return
    #
    #     if path is not None:
    #         app.router.add_route('*', path, handler, name=route_name)
    #
    #     async def _wrap_callback(cb, _):
    #         return await cb(self.dispatcher)
    #
    #     for callback in self._on_startup_webhook:
    #         app.on_startup.append(functools.partial(_wrap_callback, callback))
    #
    #     async def _on_shutdown(_):
    #         await self._shutdown_webhook()
    #
    #     app.on_shutdown.append(_on_shutdown)
    #     app[APP_EXECUTOR_KEY] = self
    #     app[BOT_DISPATCHER_KEY] = self.dispatcher
    #     app[self._identity] = datetime.datetime.now()
    #     app['_check_ip'] = self.check_ip


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
