from typing import Union, Optional, Any, TextIO, Dict
from .base_processor import BaseProcessor
from os.path import isdir, isfile
from io import TextIOWrapper
from os import listdir

try:
    import ujson as json
except ImportError:
    import json


class JSONProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()

    def _verify(self):
        for lang, data in self.texts.items():
            if data.get('start') is None:
                raise RuntimeError(f'\"start\" menu is undefined for {lang}! *Nervous paw shaking*')

    def _add_text(self, text_data: dict):
        for lang, text in text_data.items():
            if lang not in self.texts:
                self.texts[lang] = text
            else:
                self.texts[lang].update(text)

    def add_texts(self, texts: Union[Dict[str, Any], TextIO, str] = 'translations',
                  is_widget: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Assigns a required piece of texts to use later
        :param texts: Dictionary or JSON containing texts, path to a file or path to a directory containing texts
        :param is_widget: Set true if text path is for a widget
        :return: Processed texts
        """
        processed_texts: Dict[str, Dict[str, Any]] = dict()
        processed_json: Optional[Dict[str, Any]] = None

        if isinstance(texts, str):
            if isdir(texts):  # Path to directory containing translations
                text_list = listdir(texts)
                for file in text_list:
                    if file.endswith('.json'):
                        with open(f'{texts}/{file}', 'r', encoding='utf-8') as text_file:
                            processed_json = json.load(text_file)
                            lang: Optional[str] = processed_json.get('lang')
                            if lang is None:
                                raise ValueError(f'The supplied translation file does not contain a language '
                                                 f'definition ("lang" field)')

                            if is_widget and lang not in self.texts.keys():  # Ignore extra languages for widgets
                                continue

                            processed_texts[lang] = processed_json
                self._add_text(text_data=processed_texts)
                if not is_widget:
                    self._verify()
                return processed_texts

            elif not isfile(texts):  # String JSON
                processed_json = json.loads(texts)
            elif isfile(texts):  # File path
                with open(texts, 'r', encoding='utf-8') as file:
                    processed_json = json.load(file)

        elif isinstance(texts, TextIOWrapper):  # IO JSON file
            processed_json = json.load(texts)
        else:
            raise ValueError('No valid text path, text or language supplied')
        if processed_json:
            lang: Optional[str] = processed_json.get('lang')
            if lang is None:
                raise ValueError(f'The supplied translation file does not contain a language definition ("lang" field)')
            processed_texts[lang] = processed_json

        self._add_text(text_data=processed_texts)
        if not is_widget:
            self._verify()
        return processed_texts

    @property
    def processor_type(self) -> str:
        return 'json'
