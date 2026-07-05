from typing import Dict, List
from dataclasses import dataclass, field
from kirjava import load as kirjava_load

from mcntools.core import BackupManager

@dataclass
class ClassFileInfo:
    path: str
    bak_path: str = field(init=False)
    has_backup: bool = False
    has_original: bool = False
    translations: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.bak_path = BackupManager.create_backup_path(self.path)

class ClassFileProcessor:

    def __init__(self):
        self._class_cache: Dict[str, ClassFileInfo] = {}

    def get_class_info(self, path: str) -> ClassFileInfo:
        if path not in self._class_cache:
            self._class_cache[path] = ClassFileInfo(path)
        return self._class_cache[path]

    @staticmethod
    def extract_constants(path: str, file_data: bytes) -> Dict[int, str]:
        cf = kirjava_load(file_data)
        result = {}
        for idx, entry in cf.constant_pool:
            if getattr(entry.type, 'name', None) == 'java/lang/String':
                result[idx] = entry.value
        return result

    @staticmethod
    def apply_translations(path: str, translations: Dict[str, str], file_data: bytes, output_path: str) -> int:
        if not translations:
            return 0

        try:
            cf = kirjava_load(file_data)
            count = 0
            for idx, entry in cf.constant_pool:
                if entry:
                    if entry.value in translations:
                        trans = translations[entry.value]
                        if trans != entry:
                            entry.value = trans
                            count += 1
            if count > 0:
                with open(output_path, 'wb') as f:
                    cf.write(f)
            return count
        except Exception:
            return 0

    def rename_class(self, old_path: str, new_path: str, backup_path: str = None) -> None:
        if old_path in self._class_cache:
            info = self._class_cache.pop(old_path)
            info.path = new_path
            if backup_path:
                info.bak_path = backup_path
            self._class_cache[new_path] = info

    def get_all_paths(self) -> List[str]:
        return list(self._class_cache.keys())