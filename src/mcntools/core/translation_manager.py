import json
import os
from typing import Dict, List

from mcntools.config import BACKUP_EXT
from mcntools.core.backup_manager import BackupManager
from mcntools.core.class_processor import ClassFileProcessor
from mcntools.core.jar_handler import JarFileHandler


class TranslationManager:

    def __init__(self, jar_name: str, file_handler: JarFileHandler, class_processor: ClassFileProcessor, backup_manager: BackupManager):
        self.jar_name = jar_name
        self.file_handler = file_handler
        self.class_processor = class_processor
        self.backup_manager = backup_manager
        self._translations_file: Optional[str] = None
        self._dirty: bool = False

    def set_translations_file(self, path: str) -> None:
        self._translations_file = path

    def load_translations(self) -> None:
        if not self._translations_file or not os.path.exists(self._translations_file):
            return
        try:
            with open(self._translations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for path, trans in data.items():
                    info = self.class_processor.get_class_info(path)
                    info.translations.update(trans)
        except (json.JSONDecodeError, OSError):
            pass

    def save_translations(self) -> None:
        if not self._dirty or not self._translations_file:
            return

        data = {}
        for path in self.class_processor.get_all_paths():
            info = self.class_processor.get_class_info(path)
            if info.translations:
                data[path] = dict(sorted(info.translations.items()))

        os.makedirs(os.path.dirname(self._translations_file), exist_ok=True)
        with open(self._translations_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        self._dirty = False
        self.file_handler.files[f"{self.jar_name}.json"] = self._translations_file

    def get_translations(self, path: str) -> Dict[str, str]:
        return self.class_processor.get_class_info(path).translations.copy()

    def update_translation(self, path: str, original: str, translation: str) -> None:
        info = self.class_processor.get_class_info(path)
        if not info.has_backup and info.has_original:
            self.backup_manager.create_backup(path)
            info.has_backup = True
        info.translations[original] = translation
        self._dirty = True

    def remove_translation(self, path: str, original: str) -> None:
        info = self.class_processor.get_class_info(path)
        if original in info.translations:
            del info.translations[original]
            self._dirty = True

    def batch_update(self, items: List[Dict], translations: Dict[str, str]) -> None:
        for item in items:
            original = item['原文']
            if original in translations:
                self.update_translation(item['_file'], item['_original'], translations[original])

    def batch_delete(self, items: List[Dict]) -> None:
        for item in items:
            self.remove_translation(item['_file'], item['_original'])

    def extract_and_save(self, paths: List[str], force_save: bool = False) -> int:
        count = 0
        for path in paths:
            if not self.file_handler.file_exists(path):
                continue

            info = self.class_processor.get_class_info(path)
            info.has_original = True
            info.has_backup = self.backup_manager.has_backup(path)

            load_path = self.backup_manager.get_backup_path(path) if info.has_backup else path
            file_data = self.file_handler.read_file(load_path)
            if not file_data:
                continue

            strings = self.class_processor.extract_constants(load_path, file_data)

            if not strings:
                continue

            for text in strings.values():
                if text not in info.translations:
                    info.translations[text] = text

            if any(o != t for o, t in info.translations.items()) and not info.has_backup:
                self.backup_manager.create_backup(path)
                info.has_backup = True
                self._dirty = True
            count += 1

        self._dirty = force_save or self._dirty
        self.save_translations()
        return count

    def apply_to_class(self, path: str) -> int:
        info = self.class_processor.get_class_info(path)
        if not info.translations or not self.file_handler.file_exists(path):
            return 0

        file_data = self.file_handler.read_file(path)
        if not file_data:
            return 0

        output_path = self.file_handler.files[path]
        return self.class_processor.apply_translations(path, info.translations, file_data, output_path)

    def scan_and_process(self) -> None:
        self.load_translations()

        class_paths = {f for f in self.file_handler.files
                      if f.endswith('.class') and not f.endswith(BACKUP_EXT)}
        bak_paths = {f for f in self.file_handler.files
                    if f.endswith(f'.class{BACKUP_EXT}')}

        for path in class_paths:
            self._process_class(path)

        for bak_path in bak_paths:
            path = bak_path[:-4]
            if path not in class_paths:
                if self.backup_manager.restore_backup(path):
                    info = self.class_processor.get_class_info(path)
                    info.has_original = True
                    if info.translations:
                        self.apply_to_class(path)

        if self._dirty:
            self.save_translations()

        if self._translations_file and os.path.exists(self._translations_file):
            self.file_handler.files[f"{self.jar_name}.json"] = self._translations_file

    def _process_class(self, path: str) -> None:
        info = self.class_processor.get_class_info(path)
        info.has_original = self.file_handler.file_exists(path)
        info.has_backup = self.backup_manager.has_backup(path)

        if info.has_backup and info.has_original and not info.translations:
            self._generate_from_diff(path)

    def _generate_from_diff(self, path: str) -> None:
        info = self.class_processor.get_class_info(path)
        bak_path = self.backup_manager.get_backup_path(path)

        if not self.file_handler.file_exists(bak_path) or not self.file_handler.file_exists(path):
            return

        try:
            bak_data = self.file_handler.read_file(bak_path)
            cur_data = self.file_handler.read_file(path)
            if not bak_data or not cur_data:
                return

            bak_strings = self.class_processor.extract_constants(bak_path, bak_data)
            cur_strings = self.class_processor.extract_constants(path, cur_data)

            new_trans = {}
            for idx, text in cur_strings.items():
                if idx in bak_strings:
                    bak_text = bak_strings[idx]
                    if bak_text != text:
                        new_trans[bak_text] = text
                else:
                    new_trans[text] = text

            if new_trans:
                info.translations.update(new_trans)
                self._dirty = True
        except Exception:
            pass
