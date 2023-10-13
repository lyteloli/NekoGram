from typing import Union, Optional, Any, TextIO, Dict
from os.path import isdir, isfile
from io import TextIOWrapper
from os import listdir

try:
    import yaml
except ImportError:
    raise ImportError('Install `pyyaml` to use `YAMLProcessor`!')

from .base_processor import BaseProcessor


class YAMLProcessor(BaseProcessor):
    def __init__(self, validate_start: bool = True):
        """
        Initialize YAMLProcessor.
        :param validate_start: Whether to check `start` object exists for each language.
        """
        super().__init__(validate_start=validate_start)

    def add_texts(self, texts: Union[Dict[str, Any], TextIO, str] = 'translations', is_widget: bool = False):
        """
        Assigns a required piece of texts to use later.
        :param texts: Dictionary or YAML containing texts, path to a file or path to a directory containing texts.
        :param is_widget: Set true if text path is for a widget.
        :return: Processed texts.
        """
        processed_data: Optional[Dict[str, Any]] = None

        if isinstance(texts, str):
            if isdir(texts):  # Path to directory containing translations
                text_list = listdir(texts)
                for file in text_list:
                    if file.endswith('.yml'):
                        with open(f'{texts}/{file}', 'r', encoding='utf-8') as text_file:
                            processed_data = yaml.safe_load(text_file)
                            lang: Optional[str] = processed_data.get('lang')
                            if lang is None:
                                raise ValueError(
                                    f'The supplied translation file does not contain a language '
                                    f'definition ("lang" field)'
                                )

                            if is_widget and lang not in self.texts.keys():  # Ignore extra languages for widgets
                                continue

                            self._add_text(text_data={lang: processed_data})
                if not is_widget:
                    self._verify()
                return

            elif not isfile(texts):  # String YAML
                processed_data = yaml.safe_load(texts)
            elif isfile(texts):  # File path
                with open(texts, 'r', encoding='utf-8') as file:
                    processed_data = yaml.safe_load(file)

        elif isinstance(texts, TextIOWrapper):  # IO YAML file
            processed_data = yaml.safe_load(texts)
        else:
            raise ValueError('No valid text path, text or language supplied')
        if processed_data:
            lang: Optional[str] = processed_data.get('lang')
            if lang is None:
                raise ValueError(f'The supplied translation file does not contain a language definition ("lang" field)')

            self._add_text(text_data={lang: processed_data})
        if not is_widget:
            self._verify()
        return

    @staticmethod
    def convert_data(data: Dict[str, Any], output_path: str):
        """
        Convert input dictionary to YAML file format.
        :param data: Input data dictionary.
        :param output_path: Output file path.
        """
        if not output_path.endswith('.yml'):
            output_path = f'{output_path}.yml'

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)
