from typing import Union, Dict, Any, TextIO
from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    def __init__(self):
        self.texts: Dict[str, Dict[str, Any]] = dict()

    @staticmethod
    @abstractmethod
    def add_texts(texts: Union[Dict[str, Any], TextIO, str] = 'translations', is_widget: bool = False):
        pass

    @property
    @abstractmethod
    def processor_type(self) -> str:
        return 'base'
