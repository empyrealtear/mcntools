from dataclasses import dataclass, field
from typing import Dict

from mcntools.core.jar_handler import BackupManager


@dataclass
class ClassFileInfo:
    path: str
    bak_path: str = field(init=False)
    has_backup: bool = False
    has_original: bool = False
    translations: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.bak_path = BackupManager.create_backup_path(self.path)


@dataclass
class TranslationItem:
    file_path: str
    index: int
    original: str
    translation: str = ""

    @property
    def is_translated(self) -> bool:
        return bool(self.translation) and self.translation != self.original

    def to_dict(self) -> Dict:
        return {
            '文件': self.file_path,
            '索引': self.index,
            '原文': self.original.replace('\n', '\\n').replace('\r', '\\r'),
            '译文': self.translation.replace('\n', '\\n').replace('\r', '\\r') if self.translation else '',
            '_file': self.file_path,
            '_original': self.original
        }