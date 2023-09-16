from NekoGram import Neko, Menu, NekoRouter
from aiogram import types


ROUTER: NekoRouter = NekoRouter(name='admins')


@ROUTER.function()
async def widget_admins_new(_: Menu, message: types.Message, neko: Neko):
    admin_id: int = int(message.text)

    if not await neko.storage.check('SELECT id FROM nekogram_users WHERE id = %s', admin_id) or \
            await neko.storage.check('SELECT id FROM nekogram_admins WHERE id = %s', admin_id):
        data = await neko.build_menu(name='widget_admins', obj=message)
        await data.send_message()
    insert_id = await neko.storage.apply('INSERT INTO nekogram_admins (id) VALUES (%s)', admin_id)
    data = await neko.build_menu(name='widget_admins_item', obj=message, callback_data=insert_id)
    await data.send_message()


@ROUTER.function()
async def widget_admins_delete_y(data: Menu, call: types.CallbackQuery, neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=call.from_user.id, bot_token=data.bot_token)
    admin_id: int = user_data['menu_admins_sel_item']
    await neko.storage.apply('DELETE FROM nekogram_admins WHERE id = %s', admin_id)
    data = await neko.build_menu(name='widget_admins', obj=call)
    await data.edit_text()
