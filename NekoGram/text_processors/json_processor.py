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
    @staticmethod
    def add_texts(texts: Union[Dict[str, Any], TextIO, str] = 'translations'):
        """
        Assigns a required piece of texts to use later
        :param texts: Dictionary or JSON containing texts, path to a file or path to a directory containing texts
        """
        processed_texts: Dict[str, Dict[str, Any]] = dict()
        processed_json: Optional[Dict[str, Any]] = None

        if isinstance(texts, str):
            if isdir(texts):  # Path to directory containing translations
                text_list = listdir(texts)
                for file in text_list:
                    if file.endswith('.json'):
                        with open(f'{texts}/{file}', 'r') as text_file:
                            processed_json = json.load(text_file)
                            lang: Optional[str] = processed_json.get('lang')
                            if lang is None:
                                raise ValueError(f'The supplied translation file does not contain a language '
                                                 f'definition ("lang" field)')
                            processed_texts[lang] = processed_json
                return processed_texts

            elif not isfile(texts):  # String JSON
                processed_json = json.loads(texts)
            elif isfile(texts):  # File path
                with open(texts, 'r') as file:
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

        return processed_texts

    @property
    def processor_type(self) -> str:
        return 'json'
