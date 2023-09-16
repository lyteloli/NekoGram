from aiogram.types import User, InlineKeyboardMarkup, InlineKeyboardButton, Message
from typing import Dict, List
try:
    import ujson as json
except ImportError:
    import json

from NekoGram import Neko, Menu, NekoRouter


ROUTER: NekoRouter = NekoRouter(name='broadcast')


@ROUTER.formatter()
async def widget_broadcast(data: Menu, _: User, neko: Neko):
    if await neko.storage.check('SELECT id FROM nekogram_users;') < 2:
        await data.obj.answer(text=data.extras['alt_text'], show_alert=True)
        data.break_execution()


@ROUTER.formatter()
async def widget_broadcast_post_markup(data: Menu, user: User, neko: Neko):
    user_data = await neko.storage.get_user_data(user_id=user.id)
    raw_markup: List[List[Dict[str, str]]] = user_data.get('widget_broadcast_post_markup', [])
    markup: InlineKeyboardMarkup = InlineKeyboardMarkup()
    row_index: int = 0

    for row in raw_markup:
        row_buttons = []

        button_index: int = 0
        for button in row:
            row_buttons.append(InlineKeyboardButton(
                text=button['text'], callback_data=f'widget_broadcast_remove_button#{row_index}-{button_index}'
            ))
            button_index += 1
        if button_index < 3:
            row_buttons.append(InlineKeyboardButton(
                text='➕', callback_data=f'widget_broadcast_add_button_step_1#{row_index}'
            ))
        markup.add(*row_buttons)
        row_index += 1

    await data.build(markup=markup, markup_format={'row_index': row_index})


@ROUTER.formatter()
async def widget_broadcast_add_button_step_1(data: Menu, user: User, neko: Neko):
    if isinstance(data.obj, Message):
        return
    await neko.storage.set_user_data(data={'widget_broadcast_post_row_index': data.call_data}, user_id=user.id)
