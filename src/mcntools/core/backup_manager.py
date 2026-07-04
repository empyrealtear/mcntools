import os
import shutil

from mcntools.config import BACKUP_EXT
from mcntools.core.jar_handler import JarFileHandler


class BackupManager:

    def __init__(self, file_handler: JarFileHandler):
        self.file_handler = file_handler

    def get_backup_path(self, path: str) -> str:
        return path + BACKUP_EXT

    def has_backup(self, path: str) -> bool:
        return self.file_handler.file_exists(self.get_backup_path(path))

    def create_backup(self, path: str) -> bool:
        if not self.file_handler.file_exists(path):
            return False
        try:
            data = self.file_handler.read_file(path)
            if data is not None:
                self.file_handler.write_file(self.get_backup_path(path), data)
                return True
        except OSError:
            return False
        return False

    def restore_backup(self, path: str) -> bool:
        bak_path = self.get_backup_path(path)
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