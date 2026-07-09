from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from mcntools.config import BACKUP_EXT


@dataclass
class ClassFileInfo:
    path: str
    bak_path: str = field(init=False)
    has_backup: bool = False
    has_original: bool = False
    translations: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.bak_path = f'{self.path}{BACKUP_EXT}'


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


@dataclass
class JarEntry:
    jar_id: str
    jar_path: str
    jar_name: str
    temp_dir: str
    files: Dict[str, str]
    parent_jar_id: Optional[str] = None
    nested_jar_path: Optional[str] = None
    children: List[str] = field(default_factory=list)