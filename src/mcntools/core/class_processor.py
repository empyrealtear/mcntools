from typing import Dict, List

from kirjava import load as kirjava_load

from mcntools.models.data import ClassFileInfo


class ClassFileProcessor:

    def __init__(self):
        self._class_cache: Dict[str, ClassFileInfo] = {}

    def get_class_info(self, path: str) -> ClassFileInfo:
        if path not in self._class_cache:
            self._class_cache[path] = ClassFileInfo(path)
        return self._class_cache[path]

    def extract_constants(self, path: str, file_data: bytes) -> Dict[int, str]:
        cf = kirjava_load(file_data)
        result = {}
        for entry, idx in cf.constant_pool._backward_entries.items():
            if getattr(entry.type, 'name', None) == 'java/lang/String' and entry.value:
                text = str(entry.value)
                if text.strip():
                    result[idx] = text
        return result

    def apply_translations(self, path: str, translations: Dict[str, str], file_data: bytes, output_path: str) -> int:
        if not translations:
            return 0

        try:
            cf = kirjava_load(file_data)
            count = 0
            for entry in cf.constant_pool:
                if entry and hasattr(entry, 'value') and isinstance(entry.value, str):
                    text = entry.value
                    if text in translations:
                        trans = translations[text]
                        if trans != text:
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