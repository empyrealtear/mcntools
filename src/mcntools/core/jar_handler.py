import os
import shutil
import zipfile
from typing import Dict, List, Optional

from mcntools.config import BACKUP_EXT, CLASS_EXT


class JarFileHandler:

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.files: Dict[str, str] = {}

    @staticmethod
    def encode_filename(filename: str) -> str:
        try:
            filename.encode('cp437')
            return filename
        except Exception:
            try:
                return filename.encode('utf-8').decode('cp437')
            except Exception:
                return filename

    @staticmethod
    def decode_filename(filename: str) -> str:
        name = filename
        try:
            name = filename.encode('cp437').decode('gbk')
        except Exception:
            try:
                name = filename.encode('cp437').decode('utf-8')
            except Exception:
                pass
        return name

    def extract_jar(self, jar_path: str) -> Dict[str, str]:
        self.files.clear()
        with zipfile.ZipFile(jar_path, 'r') as jar:
            for info in jar.infolist():
                if not info.filename.endswith('/'):
                    filename = JarFileHandler.decode_filename(info.filename)
                    data = jar.read(info.filename)
                    temp_path = os.path.join(self.temp_dir, filename)
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    with open(temp_path, 'wb') as f:
                        f.write(data)
                    self.files[filename] = temp_path
        return self.files

    def get_nested_jars(self) -> List[str]:
        return [path for path in self.files if path.endswith('.jar')]

    def save_jar(self, jar_path: str) -> None:
        with zipfile.ZipFile(jar_path, 'w', zipfile.ZIP_DEFLATED) as jar:
            for file_path, temp_path in self.files.items():
                if os.path.exists(temp_path):
                    jar.write(temp_path, file_path)

    def read_file(self, path: str) -> Optional[bytes]:
        if path in self.files:
            with open(self.files[path], 'rb') as f:
                return f.read()
        return None

    def write_file(self, path: str, content: bytes) -> None:
        temp_path = os.path.join(self.temp_dir, path)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, 'wb') as f:
            f.write(content)
        self.files[path] = temp_path

    def file_exists(self, path: str) -> bool:
        return path in self.files

    def get_class_files(self, folder_path: str, compare_mode: bool = False) -> List[str]:
        result = []
        for path in self.files:
            if path.startswith(folder_path + '/') and self.is_class_path(path):
                bak_path = self.create_backup_path(path)
                result.append(bak_path if compare_mode and self.file_exists(bak_path) else path)
        return result

    def is_directory(self, path: str) -> bool:
        if path in self.files:
            return False
        return any(p.startswith(path + '/') for p in self.files)

    @staticmethod
    def is_class_path(path: str) -> bool:
        return path.endswith(CLASS_EXT)

    @staticmethod
    def is_class_backup_path(path: str) -> bool:
        return path.endswith(f'{CLASS_EXT}{BACKUP_EXT}')

    @staticmethod
    def is_backup_path(path: str) -> bool:
        return path.endswith(BACKUP_EXT)

    @staticmethod
    def create_backup_path(path: str) -> str:
        return f'{path}{BACKUP_EXT}'
    
    @staticmethod
    def remove_backup_suffix(path: str) -> str:
        return path.removesuffix(BACKUP_EXT)

    def has_backup(self, path: str) -> bool:
        return self.file_exists(self.create_backup_path(path))

    def create_backup(self, path: str) -> bool:
        if not self.file_exists(path):
            return False
        data = self.read_file(path)
        if data is not None:
            self.write_file(self.create_backup_path(path), data)
            return True
        return False

    def restore_backup(self, path: str) -> bool:
        bak_path = self.create_backup_path(path)
        if not self.file_exists(bak_path):
            return False
        data = self.read_file(bak_path)
        if data is not None:
            self.write_file(path, data)
            return True
        return False

    def rename_file(self, old_path: str, new_path: str) -> bool:
        if not self.file_exists(old_path):
            return False

        old_temp = self.files[old_path]
        new_temp = os.path.join(self.temp_dir, new_path)

        os.makedirs(os.path.dirname(new_temp), exist_ok=True)
        shutil.move(old_temp, new_temp)
        self.files[new_path] = new_temp
        del self.files[old_path]
        return True
