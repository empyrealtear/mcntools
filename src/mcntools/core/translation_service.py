from typing import Dict, List, Optional

from mcntools.core.jar_handler import BackupManager
from mcntools.core.workspace_manager import WorkspaceManager
from mcntools.core.jar_entry import JarEntry
from mcntools.core.translation_manager import TranslationItem


class TranslationService:

    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace_manager = workspace_manager

    def open_jar(self, jar_path: str) -> Dict[str, str]:
        entry = self.workspace_manager.add_jar(jar_path)
        return entry.files

    def save_jar(self, jar_id: str) -> None:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return
        
        entry.translation_manager.save_translations()
        entry.jar_handler.save_jar(entry.jar_path)

    def extract_strings_from_classes(self, jar_id: str, paths: List[str]) -> int:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return 0
        return entry.translation_manager.extract_and_save(paths, True)

    def update_translation(self, jar_id: str, path: str, original: str, translation: str) -> None:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return
        
        entry.translation_manager.update_translation(path, original, translation)
        entry.translation_manager.save_translations()
        entry.translation_manager.apply_to_class(path)

    def remove_translation(self, jar_id: str, path: str, original: str) -> None:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return
        
        entry.translation_manager.remove_translation(path, original)
        entry.translation_manager.save_translations()

    def batch_update_translations(self, jar_id: str, items: List[Dict], translations: Dict[str, str]) -> None:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return
        
        entry.translation_manager.batch_update(items, translations)
        entry.translation_manager.save_translations()

    def batch_delete_translations(self, jar_id: str, items: List[Dict]) -> None:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return
        
        entry.translation_manager.batch_delete(items)
        entry.translation_manager.save_translations()

    def apply_all_translations(self, jar_id: str) -> int:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return 0
        return entry.translation_manager.apply_all_translations()

    def apply_translations_to_class(self, jar_id: str, path: str) -> int:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return 0
        return entry.translation_manager.apply_to_class(path)

    def get_class_strings(self, jar_id: str, path: str, compare_mode: bool = False) -> List[TranslationItem]:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return []
        
        info = entry.class_processor.get_class_info(path)
        load_path = BackupManager.create_backup_path(path) if info.has_backup and compare_mode else path

        file_data = entry.jar_handler.read_file(load_path)
        if not file_data:
            return []

        strings = entry.class_processor.extract_constants(load_path, file_data)
        translations = entry.translation_manager.get_translations(path)

        return [
            TranslationItem(
                file_path=path,
                index=idx,
                original=text,
                translation=translations.get(text, '')
            )
            for idx, text in strings.items()
        ]

    def get_folder_strings(self, jar_id: str, folder_path: str, extract: bool = False, compare_mode: bool = False) -> List[TranslationItem]:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return []
        
        items = []
        class_files = entry.jar_handler.get_class_files(folder_path)

        if extract:
            self.extract_strings_from_classes(jar_id, class_files)

        for path in class_files:
            items.extend(self.get_class_strings(jar_id, path, compare_mode))
        return items

    def rename_file(self, jar_id: str, old_path: str, new_path: str) -> bool:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return False
        
        if not entry.backup_manager.rename_file(old_path, new_path):
            return False

        old_assoc = BackupManager.create_backup_path(old_path)
        if entry.jar_handler.file_exists(old_assoc):
            entry.backup_manager.rename_file(old_assoc, BackupManager.create_backup_path(new_path))

        new_bak_path = entry.backup_manager.create_backup_path(new_path)
        entry.class_processor.rename_class(old_path, new_path, new_bak_path)
        return True

    def create_backup(self, jar_id: str, path: str) -> bool:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return False
        
        result = entry.backup_manager.create_backup(path)
        if result:
            info = entry.class_processor.get_class_info(path)
            info.has_backup = True
        return result

    def has_translations(self, jar_id: str, path: str) -> bool:
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return False
        return bool(entry.translation_manager.get_translations(path))

    def remove_jar(self, jar_id: str) -> bool:
        return self.workspace_manager.remove_jar(jar_id)

    def get_entry(self, jar_id: str) -> Optional[JarEntry]:
        return self.workspace_manager.get_entry(jar_id)

    def get_all_entries(self) -> List[JarEntry]:
        return self.workspace_manager.get_all_entries()

    def cleanup(self):
        self.workspace_manager.cleanup()