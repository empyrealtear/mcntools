import os
from typing import Dict, List

from mcntools.config import BACKUP_EXT
from mcntools.core.backup_manager import BackupManager
from mcntools.core.class_processor import ClassFileProcessor
from mcntools.core.jar_handler import JarFileHandler
from mcntools.core.translation_manager import TranslationManager
from mcntools.models.data import TranslationItem


class TranslationService:

    def __init__(self,
                 jar_handler: JarFileHandler,
                 backup_manager: BackupManager,
                 class_processor: ClassFileProcessor,
                 translation_manager: TranslationManager):
        self.jar_handler = jar_handler
        self.backup_manager = backup_manager
        self.class_processor = class_processor
        self.translation_manager = translation_manager
        self._current_jar_path: Optional[str] = None

    def open_jar(self, jar_path: str, temp_dir: str) -> Dict[str, str]:
        self._current_jar_path = jar_path
        jar_name = os.path.basename(jar_path)

        files = self.jar_handler.extract_jar(jar_path)
        self.translation_manager.set_translations_file(
            os.path.join(temp_dir, f"{jar_name}.json")
        )
        self.translation_manager.scan_and_process()
        return files

    def save_jar(self) -> None:
        if not self._current_jar_path:
            return
        self.translation_manager.save_translations()
        self.jar_handler.save_jar(self._current_jar_path)

    def extract_strings_from_classes(self, paths: List[str]) -> int:
        return self.translation_manager.extract_and_save(paths, True)

    def update_translation(self, path: str, original: str, translation: str) -> None:
        self.translation_manager.update_translation(path, original, translation)
        self.translation_manager.save_translations()
        self.translation_manager.apply_to_class(path)

    def remove_translation(self, path: str, original: str) -> None:
        self.translation_manager.remove_translation(path, original)
        self.translation_manager.save_translations()

    def batch_update_translations(self, items: List[Dict], translations: Dict[str, str]) -> None:
        self.translation_manager.batch_update(items, translations)
        self.translation_manager.save_translations()

    def batch_delete_translations(self, items: List[Dict]) -> None:
        self.translation_manager.batch_delete(items)
        self.translation_manager.save_translations()

    def apply_all_translations(self) -> int:
        return self.translation_manager.apply_all_translations()

    def apply_translations_to_class(self, path: str) -> int:
        return self.translation_manager.apply_to_class(path)

    def get_class_strings(self, path: str) -> List[TranslationItem]:
        info = self.class_processor.get_class_info(path)
        load_path = self.backup_manager.get_backup_path(path) if info.has_backup else path

        file_data = self.jar_handler.read_file(load_path)
        if not file_data:
            return []

        strings = self.class_processor.extract_constants(load_path, file_data)
        translations = self.translation_manager.get_translations(path)

        return [
            TranslationItem(
                file_path=path,
                index=idx,
                original=text,
                translation=translations.get(text, '')
            )
            for idx, text in strings.items()
        ]

    def get_folder_strings(self, folder_path: str, extract: bool = False) -> List[TranslationItem]:
        items = []
        class_files = self.jar_handler.get_class_files(folder_path)

        if extract:
            self.extract_strings_from_classes(class_files)

        for path in class_files:
            items.extend(self.get_class_strings(path))
        return items

    def rename_file(self, old_path: str, new_path: str) -> bool:
        if not self.backup_manager.rename_file(old_path, new_path):
            return False

        old_assoc = old_path + BACKUP_EXT
        if self.jar_handler.file_exists(old_assoc):
            self.backup_manager.rename_file(old_assoc, new_path + BACKUP_EXT)

        new_bak_path = self.backup_manager.get_backup_path(new_path)
        self.class_processor.rename_class(old_path, new_path, new_bak_path)
        return True

    def create_backup(self, path: str) -> bool:
        result = self.backup_manager.create_backup(path)
        if result:
            info = self.class_processor.get_class_info(path)
            info.has_backup = True
        return result

    def has_translations(self, path: str) -> bool:
        return bool(self.translation_manager.get_translations(path))