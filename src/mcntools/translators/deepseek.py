import json
import requests
import time
from typing import Dict, List

from mcntools.translators.base import BaseTranslator


class DeepSeekTranslator(BaseTranslator):
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    SYSTEM_PROMPT = """翻译为目标语言,参照Minecraft术语,规则:
1.保留所有占位符、颜色代码、HTML标签、数字、标点符号等特殊类型字符
2.只翻译自然语言，保持语序自然
3.返回格式：{"<原文>":"<译文>"}"""

    def __init__(self, api_key: str = '', from_code: str = 'auto', to_code: str = 'zh'):
        super().__init__(from_code, to_code)
        self.engine = 'deepseek'
        self.set_api_key(api_key)
        self._last_request_time = 0
        self._min_interval = 0.3

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self.available = bool(api_key)

    def _rate_limit(self):
        current = time.time()
        elapsed = current - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def translate(self, texts: List[str]) -> Dict[str, str]:
        result = self._check_basic_conditions(texts)
        if result is not None:
            return result

        self._rate_limit()
        to_name = self.lang_names.get(self.to_code, self.to_code)
        response = requests.post(
            self.API_URL,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': self.SYSTEM_PROMPT},
                    {'role': 'user', 'content': f"翻译成{to_name},待翻译文本:{json.dumps(texts, ensure_ascii=False)}"}
                ],
                'temperature': 0.3,
                'max_tokens': 4096,
                'top_p': 0.9
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            return self._parse_response(content, texts)
        else:
            return {text: text for text in texts}

    def _parse_response(self, content: str, texts: List[str]) -> Dict[str, str]:
        data = json.loads(content)
        return data if data else {}