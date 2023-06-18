from aiogram import types

from NekoGram import Neko, Menu, NekoRouter


ROUTER: NekoRouter = NekoRouter(name='languages')


@ROUTER.formatter()
async def widget_languages(data: Menu, _: types.User, neko: Neko):
    markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
    for lang in neko.text_processor.texts.keys():
        text = neko.get_widget_data('languages_replacements').get(lang, lang).upper()
        text = f'{chr(ord(text[0]) + 127397) + chr(ord(text[1]) + 127397)}{lang.upper()}'
        markup.add(types.InlineKeyboardButton(text=text, callback_data=f'widget_languages_set#{lang}'))
    await data.build(markup=markup)
