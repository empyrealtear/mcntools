import requests
from typing import Dict, List
from urllib3.exceptions import InsecureRequestWarning

from mcntools.translators.base import BaseTranslator

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class GoogleTranslator(BaseTranslator):
    API_URL = "https://translate.googleapis.com/translate_a/single"
    def __init__(self, from_code: str = 'auto', to_code: str = 'zh'):
        super().__init__(from_code, to_code)
        self.engine = 'google'
        self.lang_names = {**self.lang_names, 'zh': 'zh-CN'}
        self.available = True
        self._session = None
        self._init_session()

    def _init_session(self):
        self._session = requests.Session()
        self._session.verify = False

        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        })

    def translate(self, texts: List[str]) -> Dict[str, str]:
        result = self._check_basic_conditions(texts)
        if result is not None:
            return result

        result = {}
        from_lang = self.lang_names.get(self.from_code, self.from_code)
        to_lang = self.lang_names.get(self.to_code, self.to_code)

        for text in texts:
            if not text or not text.strip():
                result[text] = text
                continue

            try:
                url = self.API_URL
                params = {
                    'client': 'gtx',
                    'sl': from_lang,
                    'tl': to_lang,
                    'dt': 't',
                    'q': text,
                }

                response = self._session.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    translated = ''.join([part[0] for part in data[0] if part[0]])
                    result[text] = translated if translated else text
                else:
                    result[text] = text

            except Exception as e:
                print(f"Google 翻译失败: {e}")
                result[text] = text

        return result