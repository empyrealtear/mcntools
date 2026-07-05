import os
import shutil
import zipfile
from typing import Dict, List, Optional

from mcntools.config import BACKUP_EXT, CLASS_EXT

class JarFileHandler:

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.files: Dict[str, str] = {}

    def extract_jar(self, jar_path: str) -> Dict[str, str]:
        self.files.clear()
        with zipfile.ZipFile(jar_path, 'r') as jar:
            for info in jar.infolist():
                if not info.filename.endswith('/'):
                    data = jar.read(info.filename)
                    temp_path = os.path.join(self.temp_dir, info.filename)
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    with open(temp_path, 'wb') as f:
                        f.write(data)
                    self.files[info.filename] = temp_path
        return self.files

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

    def get_class_files(self, folder_path: str) -> List[str]:
        return [p for p in self.files
                if p.startswith(folder_path + '/')
                and BackupManager.is_class_path(p)
                and not BackupManager.is_class_backup_path(p)]

    def is_directory(self, path: str) -> bool:
        if path in self.files:
            return False
        return any(p.startswith(path + '/') for p in self.files)

class BackupManager:

    def __init__(self, file_handler: JarFileHandler):
        self.file_handler = file_handler
        
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

    def has_backup(self, path: str) -> bool:
        return self.file_handler.file_exists(self.create_backup_path(path))

    def create_backup(self, path: str) -> bool:
        if not self.file_handler.file_exists(path):
            return False
        try:
            data = self.file_handler.read_file(path)
            if data is not None:
                self.file_handler.write_file(self.create_backup_path(path), data)
                return True
        except OSError:
            return False
        return False

    def restore_backup(self, path: str) -> bool:
        bak_path = self.create_backup_path(path)
        if not self.file_handler.file_exists(bak_path):
            return False
        try:
            data = self.file_handler.read_file(bak_path)
            if data is not None:
                self.file_handler.write_file(path, data)
                return True
        except OSError:
            return False
        return False

    def rename_file(self, old_path: str, new_path: str) -> bool:
        if not self.file_handler.file_exists(old_path):
            return False

        old_temp = self.file_handler.files[old_path]
        new_temp = os.path.join(self.file_handler.temp_dir, new_path)
        try:
            os.makedirs(os.path.dirname(new_temp), exist_ok=True)
            shutil.move(old_temp, new_temp)
            self.file_handler.files[new_path] = new_temp
            del self.file_handler.files[old_path]
            return True
        except OSError:
            return False