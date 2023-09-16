from NekoGram import Neko, Menu, NekoRouter
from aiogram import types


ROUTER: NekoRouter = NekoRouter(name='admins')


@ROUTER.formatter()
async def widget_admins(data: Menu, user: types.User, neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=user.id, bot_token=data.bot_token)
    if data.call_data is not None:
        user_data['menu_admins_offset'] = data.call_data
        offset = data.call_data
    else:
        offset = user_data.get('menu_admins_offset', 0)

    user_data.pop('menu_admins_sel_item', None)
    await neko.storage.set_user_data(data=user_data, user_id=user.id, replace=True, bot_token=data.bot_token)

    found: int = 0
    markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
    async for item in neko.storage.select(
            'SELECT nu.id, nu.full_name FROM nekogram_admins a JOIN nekogram_users nu ON nu.id = a.id '
            'WHERE a.id != %s LIMIT 11 OFFSET %s', (user.id, offset)
    ):
        found += 1
        if found == 11:
            break
        markup.add(types.InlineKeyboardButton(
            text=item['full_name'], callback_data=f'widget_admins_item#{item["id"]}'
        ))

    await data.add_pagination(offset=offset, found=found, limit=10, shift_last=2)
    await data.build(markup=markup)


@ROUTER.formatter()
async def widget_admins_item(data: Menu, user: types.User, neko: Neko):
    if data.call_data:
        admin_id: int = data.call_data
        await neko.storage.set_user_data(
            data={'menu_admins_sel_item': data.call_data}, user_id=user.id, bot_token=data.bot_token
        )
    else:
        user_data = await neko.storage.get_user_data(user_id=user.id, bot_token=data.bot_token)
        admin_id: int = user_data['menu_admins_sel_item']

    admin_data = await neko.storage.get(
        'SELECT u.id, u.username, u.full_name FROM nekogram_admins a '
        'JOIN nekogram_users u ON a.id = u.id WHERE a.id = %s',
        admin_id
    )

    await data.build(text_format=admin_data)
