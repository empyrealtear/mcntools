import os
import zipfile
from typing import Dict, List, Optional

from mcntools.config import BACKUP_EXT


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
                and p.endswith('.class')
                and not p.endswith(BACKUP_EXT)]

    def is_directory(self, path: str) -> bool:
        if path in self.files:
            return False
        return any(p.startswith(path + '/') for p in self.files)