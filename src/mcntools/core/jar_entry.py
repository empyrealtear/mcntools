from dataclasses import dataclass
from typing import Dict

from mcntools.core.class_processor import ClassFileProcessor
from mcntools.core.jar_handler import JarFileHandler, BackupManager
from mcntools.core.translation_manager import TranslationManager


@dataclass
class JarEntry:
    jar_id: str
    jar_path: str
    jar_name: str
    temp_dir: str
    jar_handler: JarFileHandler
    backup_manager: BackupManager
    class_processor: ClassFileProcessor
    translation_manager: TranslationManager
    files: Dict[str, str]