from NekoGram import Neko, Bot
import json


def test_json_text_processor():
    neko = Neko(bot=Bot(token='0:0', validate_token=False), validate_text_names=False)
    raw_json = '{"x": {"text": "hello"} }'
    neko.add_texts(texts=raw_json, lang='en')
    assert neko.texts['en'] == json.loads(raw_json)
