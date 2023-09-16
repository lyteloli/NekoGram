from aiogram import exceptions as aiogram_exc, types
from typing import Union, Dict, List
from asyncio import sleep
from io import BytesIO

from NekoGram import Neko, Menu, NekoRouter
from NekoGram.utils import telegraph_upload
from . import utils


ROUTER: NekoRouter = NekoRouter(name='broadcast')


@ROUTER.function()
async def widget_broadcast(_: Menu, message: Union[types.Message, types.CallbackQuery], neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=message.from_user.id)
    user_data.pop('menu')
    user_data['widget_broadcast_post_caption'] = message.html_text if message.text or message.caption else None
    if message.content_type != 'text':  # Upload non-text posts to Telegraph
        if message.photo:
            f = await (max(message.photo, key=lambda c: c.width)).download(destination=BytesIO())
        else:
            f = await getattr(message, message.content_type).download(destination=BytesIO())
        url = await telegraph_upload(f)
        user_data['widget_broadcast']['file_id'] = url
    user_data['widget_broadcast_content_type'] = message.content_type

    await neko.storage.set_user_data(data=user_data, user_id=message.from_user.id, replace=True)
    data = await neko.build_menu(name='widget_broadcast_post', obj=message)
    await data.send_message()


@ROUTER.function()
async def widget_broadcast_post_preview(_: Menu, call: Union[types.Message, types.CallbackQuery], neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=call.from_user.id)

    await call.message.delete()

    await utils.send_post(user_data=user_data, chat_id=call.from_user.id, neko=neko)

    data = await neko.build_menu(name='widget_broadcast_post', obj=call)
    await data.send_message()


@ROUTER.function()
async def widget_broadcast_remove_button(data: Menu, call: Union[types.Message, types.CallbackQuery], neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=call.from_user.id)
    row_index: int = int(data.call_data.split('-')[0])
    button_index: int = int(data.call_data.split('-')[1])
    post_markup: List[List[Dict[str, str]]] = user_data['widget_broadcast_post_markup']

    del post_markup[row_index][button_index]
    if len(post_markup[row_index]) == 0:
        del post_markup[row_index]
    user_data['widget_broadcast_post_markup'] = post_markup

    await neko.storage.set_user_data(data=user_data, user_id=call.from_user.id, replace=True)

    data = await neko.build_menu(name='widget_broadcast_post_markup', obj=call)

    await data.edit_message()


@ROUTER.function()
async def widget_broadcast_add_button_step_2(_: Menu, message: Union[types.Message, types.CallbackQuery], neko: Neko):
    if message.text.startswith('@'):
        message.text = message.text.replace('@', 'https://t.me/')
    user_data = await neko.storage.get_user_data(user_id=message.from_user.id)
    row_index: int = user_data['widget_broadcast_post_row_index']
    post_markup: List[List[Dict[str, str]]] = user_data.get('widget_broadcast_post_markup', [])
    if len(post_markup) == row_index:
        post_markup.append([])
    post_markup[row_index].append({
        'text': user_data['widget_broadcast_add_button_step_1']['text'], 'url': message.text
    })
    user_data['widget_broadcast_post_markup'] = post_markup
    user_data.pop('widget_broadcast_post_row_index')
    user_data.pop('menu')
    await neko.storage.set_user_data(data=user_data, user_id=message.from_user.id, replace=True)
    data = await neko.build_menu(name='widget_broadcast_post_markup', obj=message)
    await data.send_message()


@ROUTER.function()
async def widget_broadcast_broadcast(data: Menu, call: Union[types.Message, types.CallbackQuery], neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=call.from_user.id)

    total: int = await neko.storage.check('SELECT id FROM nekogram_users;')
    attempts: int = 0
    successful: int = 0
    failed: int = 0

    await call.message.edit_text(text=data.text.format(total=total, attempts=0, successful=0, failed=0))

    async for user in neko.storage.select('SELECT * FROM nekogram_users;'):
        if user['id'] == call.from_user.id:
            continue

        attempts += 1
        while True:
            try:
                await utils.send_post(user_data=user_data, chat_id=user['id'], neko=neko)
                successful += 1
                break
            except aiogram_exc.RetryAfter as e:
                await sleep(e.timeout)
            except aiogram_exc.TelegramAPIError:
                failed += 1
                break
            await sleep(.2)

        if attempts % 5 == 0:
            await call.message.edit_text(text=data.text.format(
                total=total, attempts=attempts, successful=successful, failed=failed
            ))

    for key in user_data.copy().keys():
        if key.startswith('widget_broadcast'):
            user_data.pop(key)
    user_data.pop('menu')
    await neko.storage.set_user_data(data=user_data, user_id=call.from_user.id, replace=True)
    await data.build(text_format={
        'total': total, 'attempts': attempts, 'successful': successful, 'failed': failed
    }, allowed_buttons=[2])
    await data.edit_message()
