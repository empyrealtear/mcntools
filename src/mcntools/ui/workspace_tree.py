import os
import tkinter as tk
import ttkbootstrap as ttkb
from tkinter import simpledialog
from ttkbootstrap.dialogs import Messagebox
from typing import Dict, Optional, Set, Tuple, List

from mcntools.config import BACKUP_EXT, FONT_DEFAULT


class WorkspaceTree(ttkb.Frame):

    def __init__(self, parent, on_file_select=None,
                 on_folder_select=None, on_rename=None,
                 on_backup=None, on_save_jar=None, backup_var=None):
        super().__init__(parent)
        self.on_file_select = on_file_select
        self.on_folder_select = on_folder_select
        self.on_rename = on_rename
        self.on_backup = on_backup
        self.on_save_jar = on_save_jar
        self.files: Dict[str, Dict[str, str]] = {}
        self._jar_id_map: Dict[str, str] = {}
        self.current_path: Optional[Tuple[str, str]] = None
        self.show_backup = False
        self.translation_checker = None
        self.backup_var = backup_var

        self._init_ui()
        self._init_context_menus()

    def _init_ui(self):
        tree_frame = ttkb.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttkb.Treeview(tree_frame, show='tree', selectmode='browse')
        self.tree.tag_configure('translated', foreground='#00bc8c', font=(*FONT_DEFAULT, 'bold'))
        self.tree.tag_configure('backup', foreground='#ff6b35', font=(*FONT_DEFAULT, 'italic'))
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttkb.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scroll.set)

        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Button-3>', self._show_context_menu)
        self.tree.bind('<Double-1>', self._on_double_click)

    def _init_context_menus(self):
        self.file_context_menu = tk.Menu(self.tree, tearoff=0)
        self.file_context_menu.add_command(label="打开", command=self._open_selected)
        self.file_context_menu.add_command(label="重命名", command=self._rename_selected)
        self.file_context_menu.add_command(label="备份", command=self._create_backup_selected)
        self.file_context_menu.add_command(label="删除", command=self._delete_selected)

        self.folder_context_menu = tk.Menu(self.tree, tearoff=0)
        self.folder_context_menu.add_command(label="提取字符串", command=self._extract_strings)
        self.folder_context_menu.add_command(label="预览字符串", command=self._preview_folder)
        self.folder_context_menu.add_separator()
        self.folder_context_menu.add_command(label="展开子项", command=self._expand_selected)
        self.folder_context_menu.add_command(label="折叠子项", command=self._collapse_selected)
        self.folder_context_menu.add_command(label="折叠其他", command=self._collapse_exclude_selected)

        self.root_context_menu = tk.Menu(self.tree, tearoff=0)
        self.root_context_menu.add_command(label="保存JAR", command=self._save_jar_selected)
        self.root_context_menu.add_command(label="移除JAR", command=self._remove_jar_selected)
        self.root_context_menu.add_separator()
        self.root_context_menu.add_command(label="展开子项", command=self._expand_selected)
        self.root_context_menu.add_command(label="折叠子项", command=self._collapse_selected)

    def toggle_backup_visibility(self):
        self.show_backup = not self.show_backup
        if self.backup_var:
            self.backup_var.set(self.show_backup)
        self.rebuild_tree()

    def _on_select(self, event):
        path = self.get_selected_path()
        if path and self.on_file_select:
            self.current_path = path
            self.on_file_select(path[0], path[1])

    def _on_double_click(self, event):
        self._open_selected()

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            path = self.get_selected_path()
            if not path:
                self.root_context_menu.post(event.x_root, event.y_root)
            elif self._is_directory(path[0], path[1]):
                self.folder_context_menu.post(event.x_root, event.y_root)
            else:
                self.file_context_menu.post(event.x_root, event.y_root)

    def _open_selected(self):
        if self.current_path and self.on_file_select:
            self.on_file_select(self.current_path[0], self.current_path[1])

    def _rename_selected(self):
        path = self.get_selected_path()
        if not path or self._is_directory(path[0], path[1]):
            Messagebox.show_warning("请选择文件进行重命名", "重命名")
            return
        jar_id, file_path = path
        old_name = os.path.basename(file_path)
        new_name = simpledialog.askstring("重命名", f"为 '{old_name}' 输入新名称：", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        if '/' in new_name or '\\' in new_name:
            Messagebox.show_error("文件名不能包含路径分隔符", "重命名失败")
            return
        new_path = os.path.join(os.path.dirname(file_path), new_name).replace('\\', '/')
        if new_path in self.files.get(jar_id, {}):
            Messagebox.show_error(f"文件 '{new_path}' 已存在", "重命名失败")
            return
        if self.on_rename and self.on_rename(jar_id, file_path, new_path):
            self.rebuild_tree()
            self.select_path(jar_id, new_path)
        else:
            Messagebox.show_error("无法重命名文件", "重命名失败")

    def _create_backup_selected(self):
        if self.current_path and self.on_backup:
            self.on_backup(self.current_path[0], self.current_path[1])

    def _delete_selected(self):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        path = self.get_path(item)
        if not path:
            return
        jar_id, file_path = path
        name = self.tree.item(item, 'text')
        if not Messagebox.yesno(f"确定要删除 '{name}' 吗？\n路径: {file_path}", "确认删除"):
            return
        if jar_id in self.files and file_path in self.files[jar_id]:
            del self.files[jar_id][file_path]
        self.tree.delete(item)
        self.current_path = None

    def _extract_strings(self):
        if self.current_path and self.on_folder_select:
            jar_id, folder_path = self.current_path
            paths = self._get_class_files(jar_id, folder_path)
            if paths:
                self.on_folder_select(jar_id, paths, extract=True)
            else:
                Messagebox.show_info("没有找到class文件", "提示")

    def _preview_folder(self):
        if self.current_path and self.on_folder_select:
            jar_id, folder_path = self.current_path
            paths = self._get_class_files(jar_id, folder_path)
            if paths:
                self.on_folder_select(jar_id, paths, extract=False)
            else:
                Messagebox.show_info("没有找到class文件", "提示")

    def _save_jar_selected(self):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item and self.tree.parent(item) == '' and self.on_save_jar:
            jar_id = self.tree.item(item, 'values')[0]
            self.on_save_jar(jar_id)

    def _remove_jar_selected(self):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item and self.tree.parent(item) == '':
            jar_id = self.tree.item(item, 'values')[0]
            jar_name = self.tree.item(item, 'text')
            if Messagebox.yesno(f"确定要移除 '{jar_name}' 吗？", "确认移除"):
                self.tree.delete(item)
                if jar_id in self.files:
                    del self.files[jar_id]
                if jar_name in self._jar_id_map:
                    del self._jar_id_map[jar_name]
                self.current_path = None

    def _expand_selected(self):
        path = self.get_selected_path()
        if path and self._is_directory(path[0], path[1]):
            self._expand(self.tree.selection()[0])
        else:
            item = self.tree.selection()[0] if self.tree.selection() else None
            if item and self.tree.parent(item) == '':
                self._expand(item)
            else:
                self.expand_all()

    def _collapse_selected(self):
        path = self.get_selected_path()
        if path and self._is_directory(path[0], path[1]):
            self._collapse(self.tree.selection()[0])
        else:
            item = self.tree.selection()[0] if self.tree.selection() else None
            if item and self.tree.parent(item) == '':
                self._collapse(item)
            else:
                self.collapse_all()

    def _collapse_exclude_selected(self):
        path = self.get_selected_path()
        if path and self._is_directory(path[0], path[1]):
            for item in self.tree.get_children():
                self._collapse(item, filter_func=lambda x: x not in path[1])
        else:
            self.collapse_all()

    def _get_class_files(self, jar_id: str, path: str) -> list:
        jar_files = self.files.get(jar_id, {})
        if path in jar_files:
            return [path] if path.endswith('.class') and not path.endswith(BACKUP_EXT) else []
        return [p for p in jar_files if p.startswith(path + '/') and p.endswith('.class') and not p.endswith(BACKUP_EXT)]

    def _is_directory(self, jar_id: str, path: str) -> bool:
        jar_files = self.files.get(jar_id, {})
        if path in jar_files:
            return False
        return any(p.startswith(path + '/') for p in jar_files)

    def get_selected_path(self) -> Optional[Tuple[str, str]]:
        sel = self.tree.selection()
        return self.get_path(sel[0]) if sel else None

    def get_path(self, item) -> Optional[Tuple[str, str]]:
        parts = []
        jar_id = None
        while item:
            text = self.tree.item(item, 'text')
            values = self.tree.item(item, 'values')
            if values and len(values) > 0:
                jar_id = values[0]
            parts.insert(0, text)
            item = self.tree.parent(item)
        if len(parts) > 1 and jar_id:
            internal_path = '/'.join(parts[1:])
            return (jar_id, internal_path)
        return None

    def expand_all(self):
        for item in self.tree.get_children():
            self._expand(item)

    def _expand(self, item):
        self.tree.item(item, open=True)
        for child in self.tree.get_children(item):
            self._expand(child)

    def collapse_all(self):
        for item in self.tree.get_children():
            self._collapse(item)

    def _collapse(self, item, filter_func=None):
        if not self.tree.item(item).get('open'):
            return
        if filter_func:
            path = self.get_path(item)
            if path and filter_func(path[1]):
                self.tree.item(item, open=False)
        else:
            self.tree.item(item, open=False)
        for child in self.tree.get_children(item):
            self._collapse(child, filter_func=filter_func)

    def select_path(self, jar_id: str, internal_path: str):
        self._navigate_path(jar_id, internal_path, select=True)

    def expand_path(self, jar_id: str, internal_path: str):
        self._navigate_path(jar_id, internal_path, select=False)

    def _navigate_path(self, jar_id: str, internal_path: str, select: bool = False, fire_callback: bool = True):
        parts = internal_path.split('/')

        def find(parent, index):
            if index >= len(parts):
                return parent
            for child in self.tree.get_children(parent):
                if self.tree.item(child, 'text') == parts[index]:
                    self.tree.item(child, open=True)
                    return find(child, index + 1)
            return None

        root_item = None
        for item in self.tree.get_children(''):
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == jar_id:
                root_item = item
                break

        if not root_item:
            return

        item = find(root_item, 0)
        if item and select:
            self.tree.selection_set(item)
            self.tree.see(item)
            self.current_path = (jar_id, internal_path)
            if fire_callback and self.on_file_select:
                self.on_file_select(jar_id, internal_path)

    def build_tree(self, files_by_jar: Dict[str, Dict[str, str]]):
        self.files = files_by_jar
        self.rebuild_tree()

    def add_jar_node(self, jar_id: str, jar_name: str, files: Dict[str, str]):
        if jar_id in self.files:
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == jar_id:
                    self.tree.delete(item)
                    break

        self.files[jar_id] = files
        self._jar_id_map[jar_name] = jar_id

        root = self.tree.insert("", "end", text=jar_name, values=(jar_id,), open=True)

        filtered = [f for f in files if not f.endswith(BACKUP_EXT) or self.show_backup]
        tree = {}
        for path in filtered:
            parts = path.split('/')
            cur = tree
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            if parts[-1]:
                cur[parts[-1]] = None

        def add(parent, data):
            for name, children in sorted(data.items()):
                if children is None:
                    file_path = self._build_path(parent, name)
                    tags = ('file',)
                    if file_path.endswith(BACKUP_EXT):
                        tags = ('file', 'backup')
                    if self.translation_checker and file_path.endswith('.class') and not file_path.endswith(BACKUP_EXT):
                        if self.translation_checker(jar_id, file_path):
                            tags = ('file', 'translated')
                    self.tree.insert(parent, "end", text=name, tags=tags)
                else:
                    node = self.tree.insert(parent, "end", text=name, tags=('dir',))
                    add(node, children)

        add(root, tree)

    def rebuild_tree(self):
        expanded_paths = self._get_expanded_paths()
        selected_path = self.get_selected_path()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for jar_id, files in self.files.items():
            jar_name = jar_id
            for name, id_ in self._jar_id_map.items():
                if id_ == jar_id:
                    jar_name = name
                    break

            root = self.tree.insert("", "end", text=jar_name, values=(jar_id,), open=True)

            filtered = [f for f in files if not f.endswith(BACKUP_EXT) or self.show_backup]
            tree = {}
            for path in filtered:
                parts = path.split('/')
                cur = tree
                for p in parts[:-1]:
                    cur = cur.setdefault(p, {})
                if parts[-1]:
                    cur[parts[-1]] = None

            def add(parent, data):
                for name, children in sorted(data.items()):
                    if children is None:
                        file_path = self._build_path(parent, name)
                        tags = ('file',)
                        if file_path.endswith(BACKUP_EXT):
                            tags = ('file', 'backup')
                        if self.translation_checker and file_path.endswith('.class') and not file_path.endswith(BACKUP_EXT):
                            if self.translation_checker(jar_id, file_path):
                                tags = ('file', 'translated')
                        self.tree.insert(parent, "end", text=name, tags=tags)
                    else:
                        node = self.tree.insert(parent, "end", text=name, tags=('dir',))
                        add(node, children)

            add(root, tree)

        for jar_id, path in expanded_paths:
            self._expand_path_no_select(jar_id, path)

        if selected_path:
            jar_id, internal_path = selected_path
            if jar_id in self.files:
                if internal_path in self.files[jar_id] or self._is_directory(jar_id, internal_path):
                    self._navigate_path(jar_id, internal_path, select=True, fire_callback=False)
                elif self.current_path and (self.current_path[0] not in self.files or 
                                           self.current_path[1] not in self.files[self.current_path[0]]):
                    self.current_path = None

    def _build_path(self, parent_item, name: str) -> str:
        parts = []
        while parent_item:
            parts.insert(0, self.tree.item(parent_item, 'text'))
            parent_item = self.tree.parent(parent_item)
        if parts:
            parts = parts[1:]
        parts.append(name)
        return '/'.join(parts)

    def _get_expanded_paths(self) -> Set[Tuple[str, str]]:
        expanded = set()

        def traverse(item, jar_id, parent_path):
            if self.tree.item(item, 'open'):
                if parent_path:
                    expanded.add((jar_id, parent_path))
                for child in self.tree.get_children(item):
                    child_name = self.tree.item(child, 'text')
                    child_path = parent_path + '/' + child_name if parent_path else child_name
                    traverse(child, jar_id, child_path)

        for root_child in self.tree.get_children(''):
            values = self.tree.item(root_child, 'values')
            jar_id = values[0] if values else self.tree.item(root_child, 'text')
            traverse(root_child, jar_id, '')

        return expanded

    def _expand_path_no_select(self, jar_id: str, path: str):
        parts = path.split('/')

        def find(parent, index):
            if index >= len(parts):
                return
            for child in self.tree.get_children(parent):
                if self.tree.item(child, 'text') == parts[index]:
                    self.tree.item(child, open=True)
                    find(child, index + 1)
                    break

        root_item = None
        for item in self.tree.get_children(''):
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == jar_id:
                root_item = item
                break

        if root_item:
            find(root_item, 0)

    def set_translation_checker(self, checker):
        self.translation_checker = checker

    def remove_jar(self, jar_id: str):
        for item in self.tree.get_children(''):
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == jar_id:
                jar_name = self.tree.item(item, 'text')
                self.tree.delete(item)
                if jar_name in self._jar_id_map:
                    del self._jar_id_map[jar_name]
                break
        if jar_id in self.files:
            del self.files[jar_id]