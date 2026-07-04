import os

FONT_FAMILY = "Microsoft YaHei"
FONT_DEFAULT = (FONT_FAMILY, 10)
BACKUP_EXT = '.bak'
CONFIG_FILE = os.path.join('.', "config.json")
WORKSPACE_DIR = os.path.join('.', '.workspace')

LANGUAGES = {
    'auto': '自动检测',
    'zh': '中文',
    'en': '英语',
    'ja': '日语',
    'ko': '韩语',
    'fr': '法语',
    'de': '德语',
    'es': '西班牙语',
    'ru': '俄语',
    'ar': '阿拉伯语',
    'pt': '葡萄牙语',
    'it': '意大利语',
    'nl': '荷兰语',
    'pl': '波兰语',
    'uk': '乌克兰语',
    'vi': '越南语',
    'th': '泰语',
    'hi': '印地语',
}

ENGINES = {
    'deepseek': {'name': 'DeepSeek', 'icon': '🐋', 'need_api_key': True, 'desc': '高质量翻译，需API Key'},
    'google': {'name': 'Google', 'icon': '🌐', 'need_api_key': False, 'desc': '免费快速，无需API Key'},
}
