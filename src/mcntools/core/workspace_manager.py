import os
import shutil
from typing import Dict, List, Optional

from mcntools.config import WORKSPACE_DIR
from mcntools.core.backup_manager import BackupManager
from mcntools.core.class_processor import ClassFileProcessor
from mcntools.core.jar_handler import JarFileHandler
from mcntools.core.translation_manager import TranslationManager
from mcntools.core.jar_entry import JarEntry


class WorkspaceManager:
    def __init__(self):
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        self.workspace_dir = WORKSPACE_DIR
        self._entries: Dict[str, JarEntry] = {}
        self._id_counter = 0

    def add_jar(self, jar_path: str) -> JarEntry:
        jar_name = os.path.basename(jar_path)
        
        for existing_entry in self._entries.values():
            if existing_entry.jar_path == jar_path:
                return self._reload_jar(existing_entry)
        
        jar_id = f"jar_{self._id_counter}"
        self._id_counter += 1
        
        jar_temp_dir = os.path.join(self.workspace_dir, jar_id)
        os.makedirs(jar_temp_dir, exist_ok=True)
        
        jar_handler = JarFileHandler(jar_temp_dir)
        backup_manager = BackupManager(jar_handler)
        class_processor = ClassFileProcessor()
        translation_manager = TranslationManager(
            jar_name,
            jar_handler,
            class_processor,
            backup_manager
        )
        
        files = jar_handler.extract_jar(jar_path)
        
        translation_manager.set_translations_file(
            os.path.join(jar_temp_dir, f"{jar_name}.json")
        )
        translation_manager.scan_and_process()
        
        entry = JarEntry(
            jar_id=jar_id,
            jar_path=jar_path,
            jar_name=jar_name,
            temp_dir=jar_temp_dir,
            jar_handler=jar_handler,
            backup_manager=backup_manager,
            class_processor=class_processor,
            translation_manager=translation_manager,
            files=files
        )
        
        self._entries[jar_id] = entry
        return entry

    def _reload_jar(self, entry: JarEntry) -> JarEntry:
        if os.path.exists(entry.temp_dir):
            shutil.rmtree(entry.temp_dir)
        os.makedirs(entry.temp_dir, exist_ok=True)
        
        entry.jar_handler = JarFileHandler(entry.temp_dir)
        entry.backup_manager = BackupManager(entry.jar_handler)
        entry.class_processor = ClassFileProcessor()
        entry.translation_manager = TranslationManager(
            entry.jar_name,
            entry.jar_handler,
            entry.class_processor,
            entry.backup_manager
        )
        
        entry.files = entry.jar_handler.extract_jar(entry.jar_path)
        
        entry.translation_manager.set_translations_file(
            os.path.join(entry.temp_dir, f"{entry.jar_name}.json")
        )
        entry.translation_manager.scan_and_process()
        
        return entry

    def remove_jar(self, jar_id: str) -> bool:
        if jar_id not in self._entries:
            return False
        
        entry = self._entries[jar_id]
        if os.path.exists(entry.temp_dir):
            shutil.rmtree(entry.temp_dir)
        
        del self._entries[jar_id]
        return True

    def get_entry(self, jar_id: str) -> Optional[JarEntry]:
        return self._entries.get(jar_id)

    def get_all_entries(self) -> List[JarEntry]:
        return list(self._entries.values())

    def get_all_files(self) -> Dict[str, Dict[str, str]]:
        return {entry.jar_id: entry.files for entry in self._entries.values()}

    def has_entries(self) -> bool:
        return len(self._entries) > 0

    def cleanup(self):
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        
        self._entries.clear()
        self._id_counter = 0

    def __len__(self):
        return len(self._entries)