from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

from ...base_neko import BaseNeko


def assemble_markup(markup: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
    final_markup = InlineKeyboardMarkup()
    for row in markup:
        row_buttons = []
        for button in row:
            row_buttons.append(InlineKeyboardButton(text=button['text'], url=button['url']))
        final_markup.add(*row_buttons)

    return final_markup


async def send_post(user_data: dict, chat_id: int, neko: BaseNeko):
    post_data = user_data['widget_broadcast']
    post_data['content_type'] = user_data['widget_broadcast_content_type']
    post_data['caption'] = user_data.get('widget_broadcast_post_caption')
    raw_markup = user_data.get('widget_broadcast_post_markup', [])

    if post_data['content_type'] == 'text':
        await neko.bot.send_message(
            text=post_data['caption'],
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=assemble_markup(raw_markup),
            chat_id=chat_id
        )
    elif post_data['content_type'] == 'photo':
        await neko.bot.send_photo(
            photo=post_data['file_id'],
            parse_mode='HTML',
            caption=post_data['caption'],
            reply_markup=assemble_markup(raw_markup),
            chat_id=chat_id
        )
    elif post_data['content_type'] == 'video':
        await neko.bot.send_video(
            video=post_data['file_id'],
            parse_mode='HTML',
            caption=post_data['caption'],
            reply_markup=assemble_markup(raw_markup),
            chat_id=chat_id
        )
    else:
        await neko.bot.send_animation(
            animation=post_data['file_id'],
            parse_mode='HTML',
            caption=post_data['caption'],
            reply_markup=assemble_markup(raw_markup),
            chat_id=chat_id
        )
