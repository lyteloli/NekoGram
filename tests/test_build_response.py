from NekoGram import Neko, Bot
import pytest

neko = Neko(bot=Bot(token='0:0', validate_token=False), validate_text_names=False)


@pytest.mark.asyncio
async def test_build_response():
    raw_json = '{"x": {"text": "hello"} }'
    neko.add_texts(texts=raw_json, lang='en')
    data = await neko.build_text(text='x', user='en')
    assert data.data.text == 'hello'
