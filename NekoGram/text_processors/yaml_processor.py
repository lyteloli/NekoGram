from typing import Any

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

    @property
    def extensions(self) -> list[str]:
        return ['.yaml', '.yml']

    def from_str(self, texts: str) -> dict[str, Any]:
        return yaml.safe_load(texts)
