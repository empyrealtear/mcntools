import json
import os
import shutil
from typing import Dict, List, Optional

from mcntools.config import WORKSPACE_DIR, BACKUP_EXT
from mcntools.core.jar_handler import JarFileHandler
from mcntools.core.data_store import DataStore
from mcntools.core.types import JarEntry, ClassFileInfo, TranslationItem


class WorkspaceService:

    def __init__(self):
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        self.workspace_dir = WORKSPACE_DIR

    def add_jar(self, jar_path: str, jar_name: str = None, parent_jar_id: str = None, nested_jar_path: str = None, jar_id: str = None) -> JarEntry:
        if not jar_name:
            jar_name = os.path.basename(jar_path)
        if not jar_id:
            jar_id = f"jar_{DataStore.get_next_id()}"
        
        jar_temp_dir = f"{self.workspace_dir}/{jar_id}"
        os.makedirs(jar_temp_dir, exist_ok=True)
        
        jar_handler = JarFileHandler(jar_temp_dir)
        files = jar_handler.extract_jar(jar_path)
        
        translations_file = os.path.join(jar_temp_dir, f"{jar_name}.json")
        DataStore.set_translations_file(jar_id, translations_file)
        self._scan_and_process(jar_id, jar_name, jar_handler)
        
        entry = JarEntry(
            jar_id=jar_id,
            jar_path=jar_path,
            jar_name=jar_name,
            temp_dir=jar_temp_dir,
            files=files,
            parent_jar_id=parent_jar_id,
            nested_jar_path=nested_jar_path,
            children=[]
        )
        
        DataStore.add_entry(entry)
        DataStore.add_files(jar_id, files)
        DataStore.add_jar_id_map(jar_name, jar_id)
        if parent_jar_id and nested_jar_path:
            DataStore.add_nested_jar_info(jar_id, parent_jar_id, nested_jar_path)
        
        if parent_jar_id:
            parent_entry = DataStore.get_entry(parent_jar_id)
            if parent_entry:
                parent_entry.children.append(jar_id)
        
        self._process_nested_jars(jar_id, jar_handler)
        
        return entry

    def _process_nested_jars(self, jar_id: str, jar_handler: JarFileHandler):
        nested_jars = jar_handler.get_nested_jars()
        for nested_path in nested_jars:
            nested_jar_path = jar_handler.files[nested_path]
            self.add_jar(
                jar_path=nested_jar_path,
                parent_jar_id=jar_id,
                nested_jar_path=nested_path
            )

    def _reload_jar(self, entry: JarEntry) -> JarEntry:
        for child_id in entry.children:
            self.remove_jar(child_id)
        
        entry.children.clear()
        
        if os.path.exists(entry.temp_dir):
            shutil.rmtree(entry.temp_dir)
        os.makedirs(entry.temp_dir, exist_ok=True)
        
        jar_handler = JarFileHandler(entry.temp_dir)
        entry.files = jar_handler.extract_jar(entry.jar_path)
        
        translations_file = os.path.join(entry.temp_dir, f"{entry.jar_name}.json")
        DataStore.set_translations_file(entry.jar_id, translations_file)
        self._scan_and_process(entry.jar_id, entry.jar_name, jar_handler)
        DataStore.add_files(entry.jar_id, entry.files)
        self._process_nested_jars(entry.jar_id, jar_handler)
        
        return entry

    def remove_jar(self, jar_id: str) -> bool:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return False
        
        jar_ids_to_remove = self._collect_jar_ids_post_order(jar_id)
        
        for jid in jar_ids_to_remove:
            j_entry = DataStore.get_entry(jid)
            if j_entry and j_entry.parent_jar_id:
                parent_entry = DataStore.get_entry(j_entry.parent_jar_id)
                if parent_entry and jid in parent_entry.children:
                    parent_entry.children.remove(jid)
        
        for jid in jar_ids_to_remove:
            j_entry = DataStore.get_entry(jid)
            if j_entry:
                try:
                    if os.path.exists(j_entry.temp_dir):
                        shutil.rmtree(j_entry.temp_dir)
                except Exception:
                    pass
        
        for jid in jar_ids_to_remove:
            j_entry = DataStore.get_entry(jid)
            if j_entry:
                DataStore.remove_entry(jid)
                DataStore.remove_files(jid)
                DataStore.remove_jar_id_map(j_entry.jar_name)
                DataStore.remove_nested_jar_info(jid)
                DataStore.remove_node_cache_by_jar_id(jid)
                DataStore.remove_class_info_by_jar_id(jid)
                DataStore.remove_translations_file(jid)
        
        return True

    def _collect_jar_ids_post_order(self, jar_id: str) -> list:
        result = []
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return result
        
        for child_id in entry.children:
            result.extend(self._collect_jar_ids_post_order(child_id))
        
        result.append(jar_id)
        return result

    def save_jar(self, jar_id: str) -> None:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return
        
        for child_id in entry.children:
            self.save_jar(child_id)
        
        self.apply_all_translations(jar_id)
        self._save_translations(jar_id)
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        if entry.parent_jar_id:
            parent_entry = DataStore.get_entry(entry.parent_jar_id)
            if parent_entry and entry.nested_jar_path:
                jar_handler.save_jar(parent_entry.files[entry.nested_jar_path])
        else:
            jar_handler.save_jar(entry.jar_path)

    def extract_strings_from_classes(self, jar_id: str, paths: List[str]) -> int:
        return self._extract_and_save(jar_id, paths, True)

    def update_translation(self, jar_id: str, path: str, original: str, translation: str) -> None:
        info = DataStore.get_class_info(jar_id, path)
        if not info.has_backup and info.has_original:
            self._create_backup(jar_id, path)
            info.has_backup = True
        info.translations[original] = translation
        DataStore.set_dirty(jar_id)
        self._save_translations(jar_id)
        self.apply_translations_to_class(jar_id, path)

    def remove_translation(self, jar_id: str, path: str, original: str) -> None:
        info = DataStore.get_class_info(jar_id, path)
        if original in info.translations:
            del info.translations[original]
            DataStore.set_dirty(jar_id)
        self._save_translations(jar_id)
        self.apply_translations_to_class(jar_id, path)

    def batch_update_translations(self, jar_id: str, items: List[Dict], translations: Dict[str, str]) -> None:
        for item in items:
            original = item['原文']
            if original in translations:
                self.update_translation(jar_id, item['_file'], item['_original'], translations[original])
        self._save_translations(jar_id)

    def batch_delete_translations(self, jar_id: str, items: List[Dict]) -> None:
        for item in items:
            self.remove_translation(jar_id, item['_file'], item['_original'])
        self._save_translations(jar_id)
        self.apply_all_translations(jar_id)

    def apply_all_translations(self, jar_id: str) -> int:
        count = 0
        for path in DataStore.get_class_paths_by_jar_id(jar_id):
            info = DataStore.get_class_info(jar_id, path)
            if info.translations:
                count += self.apply_translations_to_class(jar_id, path)
        
        for child_id in DataStore.get_entry(jar_id).children:
            count += self.apply_all_translations(child_id)
        
        return count

    def apply_translations_to_class(self, jar_id: str, path: str) -> int:
        info = DataStore.get_class_info(jar_id, path)
        
        if not info.translations and info.has_backup:
            self._restore_original_class(jar_id, path)
            return 0
        
        entry = DataStore.get_entry(jar_id)
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        if not jar_handler.file_exists(path):
            return 0
        
        input_path = jar_handler.files[JarFileHandler.create_backup_path(path) if info.has_backup else path]
        output_path = jar_handler.files[JarFileHandler.remove_backup_suffix(path)]
        return DataStore.apply_translations(input_path, info.translations, output_path)

    def _restore_original_class(self, jar_id: str, path: str):
        info = DataStore.get_class_info(jar_id, path)
        entry = DataStore.get_entry(jar_id)
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        bak_path = JarFileHandler.create_backup_path(path)
        if jar_handler.file_exists(bak_path):
            os.remove(jar_handler.files[path])
            os.rename(jar_handler.files[bak_path], jar_handler.files[path])
            del jar_handler.files[bak_path]
        
        entry.files = jar_handler.files
        info.has_backup = False
        info.translations.clear()
        DataStore.set_dirty(jar_id)

    def get_class_strings(self, jar_id: str, path: str, compare: bool = True) -> List[TranslationItem]:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return []
        
        original_path = JarFileHandler.remove_backup_suffix(path)
        info = DataStore.get_class_info(jar_id, original_path)
        
        if info.has_backup and compare:
            bak_full_path = os.path.join(entry.temp_dir, info.bak_path.replace('/', os.sep))
            load_path = info.bak_path if os.path.exists(bak_full_path) else path
        else:
            load_path = path
        
        full_path = os.path.join(entry.temp_dir, load_path.replace('/', os.sep))
        strings = DataStore.extract_constants(full_path)
        return [
            TranslationItem(
                file_path=original_path,
                index=idx,
                original=text,
                translation=info.translations.get(text, '')
            )
            for idx, text in strings.items()
        ]

    # def get_folder_strings(self, jar_id: str, folder_or_files, extract: bool = False) -> List[TranslationItem]:
    #     entry = DataStore.get_entry(jar_id)
    #     if not entry:
    #         return []
        
    #     if isinstance(folder_or_files, list):
    #         class_files = folder_or_files
    #     else:
    #         jar_handler = JarFileHandler(entry.temp_dir)
    #         jar_handler.files = entry.files
    #         class_files = jar_handler.get_class_files(folder_or_files)
        
    #     files_map = {jar_id: class_files}
    #     return self.get_strings(files_map, extract=extract)

    def get_strings(self, files_map: Dict[str, List[str]], extract: bool = False, compare: bool = False) -> List[TranslationItem]:
        items = []
        for jar_id, file_paths in files_map.items():
            entry = DataStore.get_entry(jar_id)
            if not entry:
                continue
            for path in file_paths:
                load_path = path
                items.extend(self.get_class_strings(jar_id, load_path, compare=compare))
        
        if extract:
            self._save_strings_translations(files_map, items)
        
        return items

    def _save_strings_translations(self, files_map: Dict[str, List[str]], items: List[TranslationItem]):
        for jar_id in files_map:
            for item in items:
                if item.file_path in files_map[jar_id]:
                    info = DataStore.get_class_info(jar_id, item.file_path)
                    if item.original not in info.translations or not info.translations[item.original]:
                        info.translations[item.original] = item.original
        
        for jar_id in files_map:
            DataStore.set_dirty(jar_id)
            self._save_translations(jar_id)

    def rename_file(self, jar_id: str, old_path: str, new_path: str) -> bool:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return False
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        if not jar_handler.rename_file(old_path, new_path):
            return False

        old_assoc = JarFileHandler.create_backup_path(old_path)
        if jar_handler.file_exists(old_assoc):
            jar_handler.rename_file(old_assoc, JarFileHandler.create_backup_path(new_path))

        new_bak_path = JarFileHandler.create_backup_path(new_path)
        DataStore.rename_class_info(jar_id, old_path, new_path, new_bak_path)
        
        entry.files = jar_handler.files
        return True

    def delete_file(self, jar_id: str, path: str) -> bool:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return False
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        if not jar_handler.file_exists(path):
            return False
        
        os.remove(jar_handler.files[path])
        del jar_handler.files[path]
        
        bak_path = JarFileHandler.create_backup_path(path)
        if jar_handler.file_exists(bak_path):
            os.remove(jar_handler.files[bak_path])
            del jar_handler.files[bak_path]
        
        info = DataStore.get_class_info(jar_id, path)
        info.translations.clear()
        info.has_backup = False
        
        entry.files = jar_handler.files
        DataStore.set_dirty(jar_id)
        return True

    def create_backup(self, jar_id: str, path: str) -> bool:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return False
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        result = jar_handler.create_backup(path)
        if result:
            info = DataStore.get_class_info(jar_id, path)
            info.has_backup = True
        
        entry.files = jar_handler.files
        return result

    def restore_backup(self, jar_id: str, path: str) -> bool:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return False
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        result = jar_handler.restore_backup(path)
        if result:
            info = DataStore.get_class_info(jar_id, path)
            info.has_backup = False
        
        entry.files = jar_handler.files
        return result

    def has_translations(self, jar_id: str, path: str) -> bool:
        info = DataStore.get_class_info(jar_id, path)
        return bool(info.translations)

    def get_entry(self, jar_id: str) -> Optional[JarEntry]:
        return DataStore.get_entry(jar_id)

    def get_all_entries(self) -> List[JarEntry]:
        return DataStore.get_all_entries()

    def get_root_entries(self) -> List[JarEntry]:
        return DataStore.get_root_entries()

    def get_all_files(self) -> Dict[str, Dict[str, str]]:
        return DataStore.get_all_files()

    def get_descendant_ids(self, jar_id: str) -> List[str]:
        return DataStore.get_descendant_ids(jar_id)

    def has_entries(self) -> bool:
        return DataStore.has_entries()

    def cleanup(self):
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        DataStore.clear_all()

    def __len__(self):
        return len(DataStore.jar_entries)

    def _load_translations(self, jar_id: str) -> None:
        translations_file = DataStore.get_translations_file(jar_id)
        if not translations_file or not os.path.exists(translations_file):
            return

        with open(translations_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for path, trans in data.items():
                info = DataStore.get_class_info(jar_id, path)
                info.translations.update(trans)


    def _save_translations(self, jar_id: str) -> None:
        if not DataStore.is_dirty(jar_id):
            return

        translations_file = DataStore.get_translations_file(jar_id)
        if not translations_file:
            return

        entry = DataStore.get_entry(jar_id)
        if not entry:
            return

        data = {}
        for path in sorted(DataStore.get_class_paths_by_jar_id(jar_id)):
            info = DataStore.get_class_info(jar_id, path)
            if info.translations:
                data[path] = dict(info.translations.items())

        os.makedirs(os.path.dirname(translations_file), exist_ok=True)
        with open(translations_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        DataStore.clear_dirty(jar_id)
        
        entry.files.update({f"{entry.jar_name}.json": translations_file})

    def _extract_and_save(self, jar_id: str, paths: List[str], force_save: bool = False) -> int:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return 0
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        count = 0
        for path in paths:
            if not jar_handler.file_exists(path):
                continue

            info = DataStore.get_class_info(jar_id, path)
            info.has_original = True
            info.has_backup = jar_handler.has_backup(path)

            load_path = JarFileHandler.create_backup_path(path) if info.has_backup else path
            full_path = os.path.join(entry.temp_dir, load_path.replace('/', os.sep))
            strings = DataStore.extract_constants(full_path)

            if not strings:
                continue

            for text in strings.values():
                if text not in info.translations:
                    info.translations[text] = text

            if any(o != t for o, t in info.translations.items()) and not info.has_backup:
                jar_handler.create_backup(path)
                info.has_backup = True
                DataStore.set_dirty(jar_id)
            count += 1

        if force_save:
            DataStore.set_dirty(jar_id)
        self._save_translations(jar_id)
        
        entry.files = jar_handler.files
        return count

    def _scan_and_process(self, jar_id: str, jar_name: str, jar_handler: JarFileHandler) -> None:
        self._load_translations(jar_id)

        class_paths = {f for f in jar_handler.files if JarFileHandler.is_class_path(f)}
        bak_paths = {f for f in jar_handler.files if JarFileHandler.is_class_backup_path(f)}

        for path in class_paths:
            self._process_class(jar_id, path, jar_handler)

        for bak_path in bak_paths:
            path = bak_path[:-4]
            if path not in class_paths:
                if jar_handler.restore_backup(path):
                    info = DataStore.get_class_info(jar_id, path)
                    info.has_original = True
                    if info.translations:
                        self.apply_translations_to_class(jar_id, path)

        if DataStore.is_dirty(jar_id):
            self._save_translations(jar_id)

        translations_file = DataStore.get_translations_file(jar_id)
        if translations_file and os.path.exists(translations_file):
            jar_handler.files[f"{jar_name}.json"] = translations_file

    def _process_class(self, jar_id: str, path: str, jar_handler: JarFileHandler) -> None:
        info = DataStore.get_class_info(jar_id, path)
        info.has_original = jar_handler.file_exists(path)
        info.has_backup = jar_handler.has_backup(path)

        if info.has_backup and info.has_original and not info.translations:
            self._generate_from_diff(jar_id, path, jar_handler)

    def _generate_from_diff(self, jar_id: str, path: str, jar_handler: JarFileHandler) -> None:
        info = DataStore.get_class_info(jar_id, path)
        bak_path = JarFileHandler.create_backup_path(path)

        if not jar_handler.file_exists(bak_path) or not jar_handler.file_exists(path):
            return

        bak_strings = DataStore.extract_constants(os.path.join(jar_handler.temp_dir, bak_path.replace('/', os.sep)))
        cur_strings = DataStore.extract_constants(os.path.join(jar_handler.temp_dir, path.replace('/', os.sep)))

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
            DataStore.set_dirty(jar_id)

    def _create_backup(self, jar_id: str, path: str) -> bool:
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return False
        
        jar_handler = JarFileHandler(entry.temp_dir)
        jar_handler.files = entry.files
        
        result = jar_handler.create_backup(path)
        entry.files = jar_handler.files
        return result