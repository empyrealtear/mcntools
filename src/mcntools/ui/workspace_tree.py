import os
import tkinter as tk
import ttkbootstrap as ttkb
from tkinter import simpledialog
from ttkbootstrap.dialogs import Messagebox
from typing import Dict, Optional, Set, Tuple, List

from mcntools.config import FONT_DEFAULT, FONT_FAMILY
from mcntools.core.jar_handler import JarFileHandler
from mcntools.core.data_store import DataStore


class WorkspaceTree(ttkb.Frame):

    def __init__(self, parent,
                 on_file_select=None,
                 on_folder_select=None,
                 on_rename=None,
                 on_backup=None,
                 on_delete_file=None,
                 on_save_jar=None,
                 on_remove_jar=None,
                 on_nested_jar_select=None,
                 on_preview_strings=None,
                 backup_var=None,
                 compare_mode_var=None):
        super().__init__(parent)

        self.on_file_select = on_file_select
        self.on_folder_select = on_folder_select
        self.on_rename = on_rename
        self.on_backup = on_backup
        self.on_delete_file = on_delete_file
        self.on_save_jar = on_save_jar
        self.on_remove_jar = on_remove_jar
        self.on_nested_jar_select = on_nested_jar_select
        self.on_extract_strings = lambda jar_id, path: on_preview_strings(jar_id, path, extract=True)
        self.on_preview_strings = on_preview_strings
        self.backup_var = backup_var
        self.compare_mode_var = compare_mode_var

        self.style = ttkb.Style()
        self._setup_base_styles()

        self.tree = ttkb.Treeview(self, show='tree', style='Workspace.Treeview')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttkb.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.config(yscrollcommand=self.scrollbar.set)

        self._setup_node_tags()
        self._setup_events()
        self.current_path: Optional[Tuple[str, str]] = None
        self.compare_mode = False

    def toggle_compare_mode(self):
        self.compare_mode = not self.compare_mode

    def apply_theme(self):
        self._setup_base_styles()
        self._setup_node_tags()

    def _setup_base_styles(self):
        self.style.configure(
            'Workspace.Treeview',
            font=FONT_DEFAULT,
            rowheight=22,
            background=self.style.colors.bg,
            foreground=self.style.colors.fg,
            fieldbackground=self.style.colors.bg
        )
        self.style.configure(
            'Workspace.Treeview.Heading',
            font=(FONT_FAMILY, 10, 'bold'),
            background=self.style.colors.dark,
            foreground=self.style.colors.fg
        )
        self.style.map(
            'Workspace.Treeview',
            background=[('selected', self.style.colors.selectbg)],
            foreground=[('selected', self.style.colors.selectfg)]
        )

    def _setup_node_tags(self):
        self.tree.tag_configure('root_jar', foreground=self.style.colors.success, font=(FONT_FAMILY, 12, 'bold'))
        self.tree.tag_configure('nested_jar', foreground=self.style.colors.info, font=(FONT_FAMILY, 12, 'bold'))
        self.tree.tag_configure('class_translated', foreground=self.style.colors.success, font=(FONT_FAMILY, 10, 'bold'))
        self.tree.tag_configure('lang_file', foreground=self.style.colors.warning, font=(FONT_FAMILY, 10, 'bold'))
        self.tree.tag_configure('backup_file', foreground=self.style.colors.warning, font=(FONT_FAMILY, 10, 'bold'))
        self.tree.tag_configure('dir', foreground=self.style.colors.fg, font=(FONT_FAMILY, 10))
        self.tree.tag_configure('file', foreground=self.style.colors.fg, font=(FONT_FAMILY, 10))

    def _setup_events(self):
        self.tree.bind('<ButtonRelease-1>', self._on_click)
        self.tree.bind('<Button-3>', self._show_context_menu)

    def _is_alt_pressed(self, event) -> bool:
        alt_mask = 0x20000
        return bool(event.state & alt_mask)

    def _on_click(self, event):
        # print(f'event.state: {event.state} -> {self._is_alt_pressed(event)}')
        item = self.tree.identify('item', event.x, event.y)
        if not item:
            return
        cache = DataStore.get_node_cache(item)
        if cache:
            jar_id, internal_path, node_type = cache
            if node_type == 'file' or node_type == 'class_translated':
                # if self.compare_mode and internal_path.endswith('.class') and self.backup_var and self.backup_var.get():
                #     bak_path = JarFileHandler.create_backup_path(internal_path)
                #     if bak_path in (DataStore.get_files(jar_id) or {}):
                #         self.current_path = (jar_id, bak_path)
                #         if self.on_file_select:
                #             self.on_file_select(jar_id, bak_path)
                #         return
                self.current_path = (jar_id, internal_path)
                if self.on_file_select:
                    self.on_file_select(jar_id, internal_path)
            elif node_type == 'backup_file':
                self.current_path = (jar_id, internal_path)
                if self.on_file_select:
                    self.on_file_select(jar_id, internal_path)
            elif node_type == 'lang_file':
                self.current_path = (jar_id, internal_path)
                if self.on_file_select:
                    self.on_file_select(jar_id, internal_path)
            elif node_type == 'dir':
                self.current_path = (jar_id, internal_path)
                files = DataStore.get_files(jar_id)
                load_files = []
                for f in files:
                    if f.startswith(internal_path) and JarFileHandler.is_class_path(f):
                        bak_path = JarFileHandler.create_backup_path(f)
                        load_files.append(bak_path if self.compare_mode and bak_path in files else f)
                if self._is_alt_pressed(event) and self.on_preview_strings:
                    self.on_preview_strings(jar_id, load_files)
                elif self.on_folder_select:
                    self.on_folder_select(jar_id, internal_path, load_files)
            elif node_type == 'nested_jar':
                self.current_path = (jar_id, '')
                entry = DataStore.get_entry(jar_id)
                if entry:
                    jar_handler = JarFileHandler(entry.temp_dir)
                    jar_handler.files = entry.files
                    class_files = jar_handler.get_class_files('')
                    if self._is_alt_pressed(event) and self.on_preview_strings:
                        self.on_preview_strings(jar_id, class_files)
                    elif self.on_nested_jar_select:
                        self.on_nested_jar_select(jar_id)

    def _show_context_menu(self, event):
        item = self.tree.identify('item', event.x, event.y)
        if not item:
            return

        cache = DataStore.get_node_cache(item)
        if not cache:
            return

        jar_id, internal_path, node_type = cache

        menu = tk.Menu(self, tearoff=0)

        if node_type == 'root_jar' or node_type == 'nested_jar':
            menu.add_command(label='保存 JAR', command=lambda: self.on_save_jar(jar_id))
            menu.add_command(label='移除 JAR', command=lambda: self._remove_jar(jar_id))
            menu.add_separator()
            # menu.add_command(label='提取字符串', command=lambda: self._extract_strings(jar_id, internal_path))
            # menu.add_command(label='预览字符串', command=lambda: self._preview_strings(jar_id, internal_path))
            # menu.add_separator()
            menu.add_command(label='展开子项', command=lambda: self._expand_children(item))
            menu.add_command(label='折叠子项', command=lambda: self._collapse_children(item))
            menu.add_command(label='折叠其他', command=lambda: self._collapse_others(item))
        elif node_type == 'dir':
            menu.add_command(label='提取字符串', command=lambda: self._extract_strings(jar_id, internal_path))
            menu.add_command(label='预览字符串', command=lambda: self._preview_strings(jar_id, internal_path))
            menu.add_separator()
            menu.add_command(label='展开子项', command=lambda: self._expand_children(item))
            menu.add_command(label='折叠子项', command=lambda: self._collapse_children(item))
            menu.add_command(label='折叠其他', command=lambda: self._collapse_others(item))
        elif node_type == 'file' or node_type == 'class_translated' or node_type == 'backup_file' or node_type == 'lang_file':
            menu.add_command(label='预览文件', command=lambda: self._preview_file(jar_id, internal_path))
            menu.add_command(label='创建备份', command=lambda: self._create_backup(jar_id, internal_path))
            menu.add_separator()
            menu.add_command(label='重命名', command=lambda: self._rename_file(jar_id, internal_path))
            menu.add_command(label='删除文件', command=lambda: self._delete_file(jar_id, internal_path))

        menu.tk_popup(event.x_root, event.y_root)

    def _expand_children(self, item):
        self.tree.item(item, open=True)
        for child in self.tree.get_children(item):
            self._expand_children(child)

    def _collapse_children(self, item):
        for child in self.tree.get_children(item):
            self._collapse_children(child)
        self.tree.item(item, open=False)

    def _collapse_others(self, item):
        parent = self.tree.parent(item)
        # TODO: 匹配排除当前选中项所在路径，即遍历的时候，路径包含在当前选中项的路径中，不折叠
        for sibling in self.tree.get_children(parent):
            if sibling != item:
                self._collapse_children(sibling)

    def _extract_strings(self, jar_id, path):
        entry = DataStore.get_entry(jar_id)
        if entry and self.on_extract_strings:
            jar_handler = JarFileHandler(entry.temp_dir)
            jar_handler.files = entry.files
            class_files = jar_handler.get_class_files(path)
            self.on_extract_strings(jar_id, class_files)

    def _preview_strings(self, jar_id, path):
        entry = DataStore.get_entry(jar_id)
        if entry and self.on_preview_strings:
            jar_handler = JarFileHandler(entry.temp_dir)
            jar_handler.files = entry.files
            class_files = jar_handler.get_class_files(path)
            self.on_preview_strings(jar_id, class_files)

    def _preview_file(self, jar_id, path):
        self.current_path = (jar_id, path)
        if self.on_file_select:
            self.on_file_select(jar_id, path)

    def _remove_jar(self, jar_id: str):
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return
        if Messagebox.yesno(f'确定要移除 JAR "{entry.jar_name}" 吗？', '确认移除') in ['Yes', '确认']:
            self.on_save_jar(jar_id)
            if self.on_remove_jar:
                self.on_remove_jar(jar_id)

    def remove_jar_node(self, jar_id: str):
        for item in self.tree.get_children():
            cache = DataStore.get_node_cache(item)
            if cache and cache[0] == jar_id:
                self.tree.delete(item)
                return
        for item in self.tree.get_children():
            self._remove_tree_item_recursive(item, jar_id)

    def _remove_tree_item_recursive(self, parent_item: str, jar_id: str):
        for child in self.tree.get_children(parent_item):
            cache = DataStore.get_node_cache(child)
            if cache and cache[0] == jar_id:
                self.tree.delete(child)
            else:
                self._remove_tree_item_recursive(child, jar_id)

    def _remove_tree_item_by_jar_id(self, jar_id: str):
        for item in self.tree.get_children():
            cache = DataStore.get_node_cache(item)
            if cache and cache[0] == jar_id:
                self.tree.delete(item)
                break

    def _restore_backup(self, jar_id: str, path: str):
        if self.on_backup:
            self.on_backup(jar_id, path, restore=True)

    def _create_backup(self, jar_id: str, path: str):
        if self.on_backup:
            self.on_backup(jar_id, path, restore=False)

    def _rename_file(self, jar_id: str, path: str):
        new_name = simpledialog.askstring('重命名', '输入新文件名:', initialvalue=os.path.basename(path))
        if new_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            if self.on_rename:
                self.on_rename(jar_id, path, new_path)
            self._refresh()

    def _delete_file(self, jar_id: str, path: str):
        if Messagebox.yesno(f'确定要删除文件 "{path}" 吗？', '确认删除') in ['Yes', '确认']:
            if self.on_delete_file:
                self.on_delete_file(jar_id, path)
            self._refresh()

    def _rename_folder(self, jar_id: str, path: str):
        new_name = simpledialog.askstring('重命名', '输入新文件夹名:', initialvalue=os.path.basename(path))
        if new_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            if self.on_rename:
                self.on_rename(jar_id, path, new_path)
            self._refresh()

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.current_path = None

    def refresh(self):
        self._refresh()

    def _refresh(self):
        expanded_paths = self._save_expanded_states()
        self.clear()
        self._populate_root_jars()
        self._restore_expanded_states(expanded_paths)

    def _save_expanded_states(self) -> set:
        expanded = set()
        def walk(node):
            if self.tree.item(node, 'open'):
                cache = DataStore.get_node_cache(node)
                if cache:
                    jar_id, internal_path, node_type = cache
                    expanded.add((jar_id, internal_path))
            for child in self.tree.get_children(node):
                walk(child)
        for root in self.tree.get_children():
            walk(root)
        return expanded

    def _restore_expanded_states(self, expanded_paths: set):
        def walk(node):
            cache = DataStore.get_node_cache(node)
            if cache:
                jar_id, internal_path, node_type = cache
                if (jar_id, internal_path) in expanded_paths:
                    self.tree.item(node, open=True)
            for child in self.tree.get_children(node):
                walk(child)
        for root in self.tree.get_children():
            walk(root)

    def _populate_root_jars(self):
        root_jar_ids = [jar_id for jar_id in DataStore.get_all_files() if jar_id not in DataStore.nested_jar_info]
        for jar_id in root_jar_ids:
            files = DataStore.get_files(jar_id) or {}
            jar_name = None
            for name, id_ in DataStore.jar_id_map.items():
                if id_ == jar_id:
                    jar_name = name
                    break
            if jar_name:
                root = self.tree.insert('', tk.END, text=jar_name, open=True, tags=('root_jar',))
                DataStore.add_node_cache(root, jar_id, '', 'root_jar')
                self._populate_tree(root, jar_id, files)
                self._populate_nested_jars(root, jar_id)

    def _populate_nested_jars(self, parent_node: str, jar_id: str):
        entry = DataStore.get_entry(jar_id)
        if not entry:
            return
        for child_id in entry.children:
            child_entry = DataStore.get_entry(child_id)
            if child_entry:
                nested_path = child_entry.nested_jar_path
                if nested_path:
                    parts = nested_path.split('/')
                    jar_name = parts[-1]
                    current_node = parent_node
                    for part in parts[:-1]:
                        existing = self.tree.get_children(current_node)
                        found = False
                        for child in existing:
                            if self.tree.item(child, 'text') == part:
                                current_node = child
                                found = True
                                break
                        if not found:
                            node_id = self.tree.insert(current_node, tk.END, text=part, open=False, tags=('dir',))
                            DataStore.add_node_cache(node_id, jar_id, '/'.join(parts[:parts.index(part)+1]), 'dir')
                            current_node = node_id
                    jar_node = self.tree.insert(current_node, tk.END, text=jar_name, open=False, tags=('nested_jar',))
                    DataStore.add_node_cache(jar_node, child_id, '', 'nested_jar')
                    nested_files = DataStore.get_files(child_id)
                    if nested_files:
                        self._populate_tree(jar_node, child_id, nested_files)
                        self._populate_nested_jars(jar_node, child_id)

    def _populate_tree(self, parent_node: str, jar_id: str, files: Dict[str, str]):
        dirs = {}
        file_list = []

        show_backup = self.backup_var.get() if self.backup_var else False

        for path in files:
            if JarFileHandler.is_class_backup_path(path) and not show_backup:
                continue
            parts = path.split('/')
            if len(parts) > 1:
                dir_path = '/'.join(parts[:-1])
                if dir_path not in dirs:
                    dirs[dir_path] = []
                dirs[dir_path].append((path, parts[-1]))
            else:
                file_list.append(path)

        for dir_path in sorted(dirs.keys()):
            parts = dir_path.split('/')
            current_node = parent_node
            for part in parts:
                existing = self.tree.get_children(current_node)
                found = False
                for child in existing:
                    if self.tree.item(child, 'text') == part:
                        current_node = child
                        found = True
                        break
                if not found:
                    node_id = self.tree.insert(current_node, tk.END, text=part, open=False, tags=('dir',))
                    DataStore.add_node_cache(node_id, jar_id, '/'.join(parts[:parts.index(part)+1]), 'dir')
                    current_node = node_id

            for full_path, file_name in sorted(dirs[dir_path], key=lambda x: x[1]):
                if file_name.endswith('.jar'):
                    continue
                tags = self._get_file_tags(jar_id, full_path)
                file_node = self.tree.insert(current_node, tk.END, text=file_name, open=False, tags=tags)
                DataStore.add_node_cache(file_node, jar_id, full_path, self._get_node_type(jar_id, full_path))

        for file_name in sorted(file_list):
            if file_name.endswith('.jar'):
                continue
            tags = self._get_file_tags(jar_id, file_name)
            file_node = self.tree.insert(parent_node, tk.END, text=file_name, open=False, tags=tags)
            DataStore.add_node_cache(file_node, jar_id, file_name, self._get_node_type(jar_id, file_name))

    def _find_nested_jar_id(self, parent_jar_id: str, nested_path: str) -> Optional[str]:
        for nested_jar_id, info in DataStore.nested_jar_info.items():
            if info.get('parent_jar_id') == parent_jar_id and info.get('nested_jar_path') == nested_path:
                return nested_jar_id
        return None

    def _get_file_tags(self, jar_id: str, path: str) -> tuple:
        tags = []
        if JarFileHandler.is_class_backup_path(path):
            tags.append('backup_file')
        elif path.endswith('.class'):
            info = DataStore.get_class_info(jar_id, path)
            if info.translations:
                tags.append('class_translated')
            else:
                tags.append('file')
        elif path.endswith('.json'):
            entry = DataStore.get_entry(jar_id)
            if entry and path == f"{entry.jar_name}.json":
                tags.append('lang_file')
            else:
                tags.append('file')
        else:
            tags.append('file')
        return tuple(tags) if tags else ('file',)

    def _get_node_type(self, jar_id: str, path: str) -> str:
        if JarFileHandler.is_class_backup_path(path):
            return 'backup_file'
        elif path.endswith('.json'):
            entry = DataStore.get_entry(jar_id)
            if entry and path == f"{entry.jar_name}.json":
                return 'lang_file'
            else:
                return 'file'
        else:
            return 'file'

    def select_jar(self, jar_id: str):
        for item in self.tree.get_children():
            cache = DataStore.get_node_cache(item)
            if cache and cache[0] == jar_id:
                self.tree.selection_set(item)
                break

    def select_path(self, jar_id: str, path: str):
        if not path:
            self.select_jar(jar_id)
            return

        for item in self.tree.get_children():
            cache = DataStore.get_node_cache(item)
            if cache and cache[0] == jar_id:
                if cache[1] == path:
                    self.tree.selection_set(item)
                    return
                self._search_path_in_tree(item, jar_id, path)

    def _search_path_in_tree(self, parent_node: str, jar_id: str, path: str):
        for child in self.tree.get_children(parent_node):
            cache = DataStore.get_node_cache(child)
            if cache and cache[0] == jar_id:
                if cache[1] == path:
                    self.tree.selection_set(child)
                    return
                self._search_path_in_tree(child, jar_id, path)

    def get_selected_path(self) -> Optional[Tuple[str, str]]:
        selected = self.tree.selection()
        if selected:
            return self.current_path
        return None

    def expand_all(self):
        def expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand(child)
        for item in self.tree.get_children():
            expand(item)

    def collapse_all(self):
        def collapse(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                collapse(child)
        for item in self.tree.get_children():
            collapse(item)

    def insert_nested_jar(self, parent_jar_id: str, nested_jar_id: str, nested_jar_path: str):
        files = DataStore.get_files(parent_jar_id)
        if not files:
            return

        parts = nested_jar_path.split('/')
        jar_name = parts[-1]

        parent_node = self._find_node_by_jar_id(parent_jar_id)
        if not parent_node:
            return

        current_node = parent_node
        for part in parts[:-1]:
            existing = self.tree.get_children(current_node)
            found = False
            for child in existing:
                if self.tree.item(child, 'text') == part:
                    current_node = child
                    found = True
                    break
            if not found:
                node_id = self.tree.insert(current_node, tk.END, text=part, open=False)
                DataStore.add_node_cache(node_id, parent_jar_id, '/'.join(parts[:parts.index(part)+1]), 'dir')
                current_node = node_id

        jar_node = self.tree.insert(current_node, tk.END, text=jar_name, open=False, tags=('nested_jar',))
        DataStore.add_node_cache(jar_node, nested_jar_id, '', 'nested_jar')
        
        nested_files = DataStore.get_files(nested_jar_id)
        if nested_files:
            self._populate_tree(jar_node, nested_jar_id, nested_files)

    def _find_node_by_jar_id(self, jar_id: str, parent: str = '') -> Optional[str]:
        for item in self.tree.get_children(parent):
            cache = DataStore.get_node_cache(item)
            if cache and cache[0] == jar_id:
                return item
            result = self._find_node_by_jar_id(jar_id, item)
            if result:
                return result
        return None

    def toggle_backup_visibility(self):
        self._refresh()

    def set_translation_checker(self, checker):
        self.translation_checker = checker

    def add_jar_node(self, jar_id, jar_name, files, parent_jar_id=None, nested_jar_path=None):
        if parent_jar_id:
            self.insert_nested_jar(parent_jar_id, jar_id, nested_jar_path)
        else:
            root = self.tree.insert('', tk.END, text=jar_name, open=True, tags=('root_jar',))
            DataStore.add_node_cache(root, jar_id, '', 'root_jar')
            self._populate_tree(root, jar_id, files)