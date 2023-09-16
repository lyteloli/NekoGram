from aiogram import types

try:
    import ujson as json
except ImportError:
    import json

from NekoGram import Neko, Menu, NekoRouter


ROUTER: NekoRouter = NekoRouter(name='stats')


@ROUTER.formatter()
async def widget_stats(data: Menu, _: types.User, neko: Neko):
    total = await neko.storage.check('SELECT id FROM nekogram_stats')
    single_user = await neko.storage.get(
        'SELECT user_id, COUNT(*) AS c, nu.full_name, nu.username '
        'FROM nekogram_stats ns JOIN nekogram_users nu ON nu.id = ns.user_id GROUP BY user_id ORDER BY c DESC LIMIT 1'
    )
    await data.build(text_format={
        'total': total,
        'user': single_user['full_name'],
        'username': f' @{single_user["username"]}' if single_user['username'] else '',
        'interactions': single_user['c']
    })
