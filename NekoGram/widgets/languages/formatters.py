from NekoGram import Neko, Menu, NekoRouter
from . import util
from aiogram import types

ROUTER: NekoRouter = NekoRouter(name='languages')


@ROUTER.formatter()
async def widget_languages(data: Menu, _: types.User, __: Neko):
    markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
    for lang in util.languages:
        text = util.replacements.get(lang, lang).upper()
        text = f'{chr(ord(text[0]) + 127397) + chr(ord(text[1]) + 127397)}{lang.upper()}'
        markup.add(types.InlineKeyboardButton(text=text, callback_data=f'widget_languages_set#{lang}'))
    await data.build(markup=markup)
