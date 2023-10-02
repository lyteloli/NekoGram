from typing import Union, Dict, Any, TextIO
from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    def __init__(self, validate_start: bool = True):
        """
        Initialize BaseProcessor.
        :param validate_start: Whether to check `start` object exists for each language.
        """
        self.texts: Dict[str, Dict[str, Any]] = dict()
        self._validate_start: bool = validate_start

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

    @staticmethod
    @abstractmethod
    def add_texts(texts: Union[Dict[str, Any], TextIO, str] = 'translations', is_widget: bool = False):
        """
        Load texts to memory.
        :param texts: Path to folder, file, TextIO or string containing translation data.
        :param is_widget: Whether the passed `texts` is related to a widget.
        """
        pass

    @staticmethod
    @abstractmethod
    def convert_data(data: Dict[str, Any], output_path: str):
        """
        Convert input dictionary to file format associated with this text processor.
        :param data: Input data dictionary.
        :param output_path: Output file path.
        """
        pass

    @property
    @abstractmethod
    def processor_type(self) -> str:
        return 'base'
