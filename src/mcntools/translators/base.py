from typing import Dict, List

from mcntools.config import LANGUAGES


class BaseTranslator:

    def __init__(self, from_code: str = 'auto', to_code: str = 'zh'):
        self.engine = ''
        self.lang_names = LANGUAGES
        self.from_code = from_code
        self.to_code = to_code
        self.api_key = ''
        self.available = False

    def translate(self, texts: List[str]) -> Dict[str, str]:
        raise NotImplementedError

    def get_status(self) -> Dict:
        return {
            'engine': self.engine,
            'from_code': self.from_code,
            'to_code': self.to_code,
            'api_key': self.api_key,
            'available': self.available,
        }

    def _check_basic_conditions(self, texts: List[str]) -> Dict[str, str]:
        if not texts:
            return {}
        if not self.available:
            return {text: text for text in texts}
        if self.from_code == self.to_code:
            return {text: text for text in texts}
        return None