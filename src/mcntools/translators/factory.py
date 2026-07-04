from mcntools.translators.base import BaseTranslator
from mcntools.translators.deepseek import DeepSeekTranslator
from mcntools.translators.google import GoogleTranslator


class TranslatorFactory:

    @staticmethod
    def create(engine: str, api_key: str = '', from_code: str = 'en', to_code: str = 'zh') -> BaseTranslator:
        if engine == 'deepseek':
            return DeepSeekTranslator(api_key, from_code, to_code)
        elif engine == 'google':
            return GoogleTranslator(from_code, to_code)
        else:
            raise ValueError(f"不支持的翻译引擎: {engine}")