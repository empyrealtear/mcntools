from typing import Dict, List, Optional, Tuple
from kirjava import ClassFile

from mcntools.core.types import JarEntry, ClassFileInfo


class DataStore:
    # 存储所有jar信息
    jar_entries: Dict[str, JarEntry] = {}
    # 存储所有jar的文件信息
    jar_files: Dict[str, Dict[str, str]] = {}
    # 存储所有jar的名称到ID的映射
    jar_id_map: Dict[str, str] = {}
    # 存储所有节点的缓存信息
    node_cache: Dict[str, Tuple[str, str, str]] = {}
    # 存储所有嵌套jar的信息
    nested_jar_info: Dict[str, Dict[str, str]] = {}
    # 存储所有类文件的信息
    class_cache: Dict[str, ClassFileInfo] = {}
    # 存储所有翻译文件的信息
    translations_files: Dict[str, str] = {}
    # 存储所有类文件的脏标志
    dirty_flags: Dict[str, bool] = {}
    # 用于生成唯一ID的计数器
    id_counter: int = 0

    @staticmethod
    def add_entry(entry: JarEntry):
        """
        添加一个jar条目到数据存储中。
        """
        DataStore.jar_entries[entry.jar_id] = entry

    @staticmethod
    def remove_entry(jar_id: str):
        """
        从数据存储中移除指定ID的jar条目。
        """
        if jar_id in DataStore.jar_entries:
            del DataStore.jar_entries[jar_id]

    @staticmethod
    def get_entry(jar_id: str) -> Optional[JarEntry]:
        """
        获取指定ID的jar条目。
        """
        return DataStore.jar_entries.get(jar_id)

    @staticmethod
    def get_all_entries() -> List[JarEntry]:
        """
        获取所有jar条目。
        """
        return list(DataStore.jar_entries.values())

    @staticmethod
    def get_root_entries() -> List[JarEntry]:
        """
        获取所有根jar条目。
        """
        return [e for e in DataStore.jar_entries.values() if e.parent_jar_id is None]

    @staticmethod
    def add_files(jar_id: str, files: Dict[str, str]):
        """
        添加一个jar的文件信息到数据存储中。
        """
        DataStore.jar_files[jar_id] = files

    @staticmethod
    def remove_files(jar_id: str):
        """
        从数据存储中移除指定ID的jar文件信息。
        """
        if jar_id in DataStore.jar_files:
            del DataStore.jar_files[jar_id]

    @staticmethod
    def get_files(jar_id: str) -> Optional[Dict[str, str]]:
        """
        获取指定ID的jar文件信息。
        """
        return DataStore.jar_files.get(jar_id)

    @staticmethod
    def get_all_files() -> Dict[str, Dict[str, str]]:
        """
        获取所有jar的文件信息。
        """
        return DataStore.jar_files.copy()

    @staticmethod
    def add_jar_id_map(jar_name: str, jar_id: str):
        """
        添加一个jar的名称到ID的映射到数据存储中。
        """
        DataStore.jar_id_map[jar_name] = jar_id

    @staticmethod
    def remove_jar_id_map(jar_name: str):
        """
        从数据存储中移除指定名称的jar ID映射。
        """
        if jar_name in DataStore.jar_id_map:
            del DataStore.jar_id_map[jar_name]

    @staticmethod
    def get_jar_id(jar_name: str) -> Optional[str]:
        """
        获取指定名称的jar ID。
        """
        return DataStore.jar_id_map.get(jar_name)

    @staticmethod
    def add_node_cache(node_id: str, jar_id: str, internal_path: str, node_type: str):
        """
        添加一个节点的缓存信息到数据存储中。
        """
        DataStore.node_cache[node_id] = (jar_id, internal_path, node_type)

    @staticmethod
    def remove_node_cache(node_id: str):
        """
        从数据存储中移除指定ID的节点缓存信息。
        """
        if node_id in DataStore.node_cache:
            del DataStore.node_cache[node_id]

    @staticmethod
    def remove_node_cache_by_jar_id(jar_id: str):
        """
        从数据存储中移除所有指定jar ID的节点缓存信息。
        """
        to_remove = [k for k, v in DataStore.node_cache.items() if v[0] == jar_id]
        for k in to_remove:
            del DataStore.node_cache[k]

    @staticmethod
    def get_node_cache(node_id: str) -> Optional[Tuple[str, str, str]]:
        """
        获取指定ID的节点缓存信息。
        """
        return DataStore.node_cache.get(node_id)

    @staticmethod
    def add_nested_jar_info(jar_id: str, parent_jar_id: str, nested_jar_path: str):
        """
        添加一个嵌套jar的信息到数据存储中。
        """
        DataStore.nested_jar_info[jar_id] = {
            'parent_jar_id': parent_jar_id,
            'nested_jar_path': nested_jar_path
        }

    @staticmethod
    def remove_nested_jar_info(jar_id: str):
        """
        从数据存储中移除指定ID的嵌套jar信息。
        """
        if jar_id in DataStore.nested_jar_info:
            del DataStore.nested_jar_info[jar_id]

    @staticmethod
    def get_nested_jar_info(jar_id: str) -> Optional[Dict[str, str]]:
        """
        获取指定ID的嵌套jar信息。
        """
        return DataStore.nested_jar_info.get(jar_id)

    @staticmethod
    def get_nested_jar_info_by_parent(parent_jar_id: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        获取所有指定父jar ID的嵌套jar信息。
        """
        return [(k, v) for k, v in DataStore.nested_jar_info.items() if v['parent_jar_id'] == parent_jar_id]

    @staticmethod
    def get_descendant_ids(jar_id: str) -> List[str]:
        """
        获取指定jar的所有子jar ID，包括间接子jar。
        """
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return []
        descendants = []
        for child_id in entry.children:
            descendants.append(child_id)
            descendants.extend(DataStore.get_descendant_ids(child_id))
        return descendants

    @staticmethod
    def _make_class_key(jar_id: str, path: str) -> str:
        """
        为指定jar ID和路径创建一个唯一的键。
        """
        return f"{jar_id}/{path}"

    @staticmethod
    def add_class_info(jar_id: str, path: str, info: ClassFileInfo):
        """
        添加一个类文件的信息到数据存储中。
        """
        key = DataStore._make_class_key(jar_id, path)
        DataStore.class_cache[key] = info

    @staticmethod
    def get_class_info(jar_id: str, path: str) -> ClassFileInfo:
        """
        获取指定类文件的信息。
        """
        key = DataStore._make_class_key(jar_id, path)
        info = DataStore.class_cache.get(key)
        if info is None:
            info = ClassFileInfo(path)
            DataStore.class_cache[key] = info
        return info

    @staticmethod
    def remove_class_info(jar_id: str, path: str):
        """
        从数据存储中移除指定类文件的信息。
        """
        key = DataStore._make_class_key(jar_id, path)
        if key in DataStore.class_cache:
            del DataStore.class_cache[key]

    @staticmethod
    def remove_class_info_by_jar_id(jar_id: str):
        """
        从数据存储中移除所有指定jar ID的类文件信息。
        """
        prefix = f"{jar_id}/"
        to_remove = [k for k in DataStore.class_cache if k.startswith(prefix)]
        for k in to_remove:
            del DataStore.class_cache[k]

    @staticmethod
    def rename_class_info(jar_id: str, old_path: str, new_path: str, backup_path: str = None):
        """
        重命名一个类文件的信息。
        """
        old_key = DataStore._make_class_key(jar_id, old_path)
        new_key = DataStore._make_class_key(jar_id, new_path)
        if old_key in DataStore.class_cache:
            info = DataStore.class_cache.pop(old_key)
            info.path = new_path
            if backup_path:
                info.bak_path = backup_path
            DataStore.class_cache[new_key] = info

    @staticmethod
    def get_class_paths_by_jar_id(jar_id: str) -> List[str]:
        """
        获取所有指定jar ID的类文件路径。
        """
        prefix = f"{jar_id}/"
        return [k[len(prefix):] for k in DataStore.class_cache if k.startswith(prefix)]

    @staticmethod
    def get_all_class_paths() -> List[str]:
        """
        获取所有类文件路径。
        """
        return list(DataStore.class_cache.keys())

    @staticmethod
    def set_translations_file(jar_id: str, path: str):
        """
        设置指定jar的翻译文件路径。
        """
        DataStore.translations_files[jar_id] = path

    @staticmethod
    def get_translations_file(jar_id: str) -> Optional[str]:
        """
        获取指定jar的翻译文件路径。
        """
        return DataStore.translations_files.get(jar_id)

    @staticmethod
    def remove_translations_file(jar_id: str):
        """
        从数据存储中移除指定jar的翻译文件路径。
        """
        if jar_id in DataStore.translations_files:
            del DataStore.translations_files[jar_id]

    @staticmethod
    def set_dirty(jar_id: str, dirty: bool = True):
        """
        设置指定jar的脏标志。
        """
        DataStore.dirty_flags[jar_id] = dirty

    @staticmethod
    def is_dirty(jar_id: str) -> bool:
        """
        检查指定jar是否脏。
        """
        return DataStore.dirty_flags.get(jar_id, False)

    @staticmethod
    def clear_dirty(jar_id: str):
        """
        清除指定jar的脏标志。
        """
        DataStore.dirty_flags[jar_id] = False

    @staticmethod
    def get_next_id() -> int:
        """
        获取下一个可用的ID。
        """
        result = DataStore.id_counter
        DataStore.id_counter += 1
        return result

    @staticmethod
    def reset_id_counter():
        """
        重置ID计数器。
        """
        DataStore.id_counter = 0

    @staticmethod
    def clear_all():
        """
        清除所有数据。
        """
        DataStore.jar_entries.clear()
        DataStore.jar_files.clear()
        DataStore.jar_id_map.clear()
        DataStore.node_cache.clear()
        DataStore.nested_jar_info.clear()
        DataStore.class_cache.clear()
        DataStore.translations_files.clear()
        DataStore.dirty_flags.clear()
        DataStore.id_counter = 0

    @staticmethod
    def has_entries() -> bool:
        """
        检查是否有任何条目。
        """
        return len(DataStore.jar_entries) > 0

    @staticmethod
    def __len__():
        return len(DataStore.jar_entries)

    @staticmethod
    def extract_constants(path: str) -> Dict[int, str]:
        with open(path, 'rb') as f:
            cf = ClassFile.read(f)
        result = {}
        for idx, entry in cf.constant_pool:
            if getattr(entry.type, 'name', None) == 'java/lang/String':
                result[idx] = entry.value
        return result

    @staticmethod
    def apply_translations(input_path: str, translations: Dict[str, str], output_path: str) -> int:
        with open(input_path, 'rb') as f:
            cf = ClassFile.read(f)
        
        count = 0
        for idx, const_entry in cf.constant_pool:
            if const_entry and const_entry.value in translations:
                trans = translations[const_entry.value]
                if trans != const_entry.value:
                    const_entry.value = trans
                    count += 1
        
        with open(output_path, 'wb') as f:
            cf.write(f)
        
        return count