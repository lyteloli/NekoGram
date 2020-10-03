from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as ikb
from NekoGram import Neko, Bot, BuildResponse
import pytest
import json

neko = Neko(bot=Bot(token='0:0', validate_token=False), validate_text_names=False)


@pytest.mark.asyncio
async def test_build_response():
    menu = {
        'x': {
            'text': 'test',
            'markup': [
                [{'text': 'button text', 'url': 'https://lyteloli.space', 'permission_level': 1}],
                [{'text': 'button text', 'url': '@NekoGramDev', 'permission_level': 3}]
            ]
        }
    }

    @neko.formatter()
    async def x(data: BuildResponse, __, ___):
        await data.data.assemble_markup(permission_level=3)

    neko.add_texts(texts=json.dumps(menu), lang='en')
    result = await neko.build_text(text='x', user='en')
    assert result.data.text == 'test'
    markup = InlineKeyboardMarkup().add(ikb(text='button text', url='https://t.me/NekoGramDev'))
    assert result.data.markup == markup
