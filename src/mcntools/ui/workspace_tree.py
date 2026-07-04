import os
import tkinter as tk
import ttkbootstrap as ttkb
from tkinter import simpledialog
from ttkbootstrap.dialogs import Messagebox
from typing import Dict, Optional, Set

from mcntools.config import BACKUP_EXT, FONT_DEFAULT


class WorkspaceTree(ttkb.Frame):

    def __init__(self, parent, on_file_select=None, on_folder_select=None, on_rename=None, on_backup=None, on_save_jar=None, backup_var=None):
        super().__init__(parent)
        self.on_file_select = on_file_select
        self.on_folder_select = on_folder_select
        self.on_rename = on_rename
        self.on_backup = on_backup
        self.on_save_jar = on_save_jar
        self.files = {}
        self.current_path = None
        self.show_backup = False
        self.translation_checker = None
        self.root_name = ""
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

    def toggle_backup_visibility(self):
        self.show_backup = not self.show_backup
        if self.backup_var:
            self.backup_var.set(self.show_backup)
        self.rebuild_tree()

    def _on_select(self, event):
        path = self.get_selected_path()
        if path and self.on_file_select:
            self.current_path = path
            self.on_file_select(path)

    def _on_double_click(self, event):
        self._open_selected()

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            path = self.get_selected_path()
            if not path or self._is_directory(path):
                self.folder_context_menu.post(event.x_root, event.y_root)
            else:
                self.file_context_menu.post(event.x_root, event.y_root)

    def _open_selected(self):
        if self.current_path and self.on_file_select:
            self.on_file_select(self.current_path)

    def _rename_selected(self):
        path = self.get_selected_path()
        if not path or self._is_directory(path):
            Messagebox.show_warning("请选择文件进行重命名", "重命名")
            return
        old_name = os.path.basename(path)
        new_name = simpledialog.askstring("重命名", f"为 '{old_name}' 输入新名称：", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        if '/' in new_name or '\\' in new_name:
            Messagebox.show_error("文件名不能包含路径分隔符", "重命名失败")
            return
        new_path = os.path.join(os.path.dirname(path), new_name).replace('\\', '/')
        if new_path in self.files:
            Messagebox.show_error(f"文件 '{new_path}' 已存在", "重命名失败")
            return
        if self.on_rename and self.on_rename(path, new_path):
            self.rebuild_tree()
            self.select_path(new_path)
        else:
            Messagebox.show_error("无法重命名文件", "重命名失败")

    def _create_backup_selected(self):
        if self.current_path and self.on_backup:
            self.on_backup(self.current_path)

    def _delete_selected(self):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        path = self.get_path(item)
        if not path:
            return
        name = self.tree.item(item, 'text')
        if not Messagebox.yesno(f"确定要删除 '{name}' 吗？\n路径: {path}", "确认删除"):
            return
        if path in self.files:
            del self.files[path]
        self.tree.delete(item)
        self.current_path = None

    def _extract_strings(self):
        if self.current_path and self.on_folder_select:
            paths = self._get_class_files(self.current_path)
            if paths:
                self.on_folder_select(paths, extract=True)
            else:
                Messagebox.show_info("没有找到class文件", "提示")

    def _preview_folder(self):
        if self.current_path and self.on_folder_select:
            paths = self._get_class_files(self.current_path)
            if paths:
                self.on_folder_select(paths, extract=False)
            else:
                Messagebox.show_info("没有找到class文件", "提示")

    def _expand_selected(self):
        path = self.get_selected_path()
        if path and self._is_directory(path):
            self._expand(self.tree.selection()[0])
        else:
            self.expand_all()

    def _collapse_selected(self):
        path = self.get_selected_path()
        if path and self._is_directory(path):
            self._collapse(self.tree.selection()[0])
        else:
            self.collapse_all()

    def _collapse_exclude_selected(self):
        path = self.get_selected_path()
        if path and self._is_directory(path):
            for item in self.tree.get_children():
                self._collapse(item, filter_func=lambda x: x not in path)
        else:
            self.collapse_all()

    def _get_class_files(self, path: str) -> list:
        if path in self.files:
            return [path] if path.endswith('.class') and not path.endswith(BACKUP_EXT) else []
        return [p for p in self.files if p.startswith(path + '/') and p.endswith('.class') and not p.endswith(BACKUP_EXT)]

    def _is_directory(self, path: str) -> bool:
        if path in self.files:
            return False
        return any(p.startswith(path + '/') for p in self.files)

    def get_selected_path(self) -> Optional[str]:
        sel = self.tree.selection()
        return self.get_path(sel[0]) if sel else None

    def get_path(self, item) -> Optional[str]:
        parts = []
        while item:
            parts.insert(0, self.tree.item(item, 'text'))
            item = self.tree.parent(item)
        return '/'.join(parts[1:]) if len(parts) > 1 else None

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
            if path and filter_func(path):
                self.tree.item(item, open=False)
        else:
            self.tree.item(item, open=False)
        for child in self.tree.get_children(item):
            self._collapse(child, filter_func=filter_func)

    def select_path(self, path: str):
        self._navigate_path(path, select=True)

    def expand_path(self, path: str):
        self._navigate_path(path, select=False)

    def _navigate_path(self, path: str, select: bool = False, fire_callback: bool = True):
        parts = path.split('/')
        root_items = self.tree.get_children('')
        if not root_items:
            return

        def find(parent, index):
            if index >= len(parts):
                return parent
            for child in self.tree.get_children(parent):
                if self.tree.item(child, 'text') == parts[index]:
                    self.tree.item(child, open=True)
                    return find(child, index + 1)
            return None

        item = find(root_items[0], 0)
        if item and select:
            self.tree.selection_set(item)
            self.tree.see(item)
            self.current_path = path
            if fire_callback and self.on_file_select:
                self.on_file_select(path)

    def build_tree(self, jar_name: str, files: Dict[str, str]):
        self.root_name = jar_name
        self.files = files
        self.rebuild_tree(jar_name)

    def rebuild_tree(self, jar_name: Optional[str] = None):
        expanded_paths = self._get_expanded_paths()
        selected_path = self.get_selected_path()

        for item in self.tree.get_children():
            self.tree.delete(item)

        if jar_name is None:
            jar_name = self.root_name if self.root_name else "JAR文件"
        root = self.tree.insert("", "end", text=jar_name, open=True)

        filtered = [f for f in self.files if not f.endswith(BACKUP_EXT) or self.show_backup]
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
                        if self.translation_checker(file_path):
                            tags = ('file', 'translated')
                    self.tree.insert(parent, "end", text=name, tags=tags)
                else:
                    node = self.tree.insert(parent, "end", text=name, tags=('dir',))
                    add(node, children)

        add(root, tree)

        for path in expanded_paths:
            self._expand_path_no_select(path)

        if selected_path:
            if selected_path in self.files or self._is_directory(selected_path):
                self._navigate_path(selected_path, select=True, fire_callback=False)
            elif self.current_path not in self.files and not self._is_directory(self.current_path):
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

    def _get_expanded_paths(self) -> Set[str]:
        expanded = set()

        def traverse(item, parent_path):
            if self.tree.item(item, 'open'):
                if parent_path:
                    expanded.add(parent_path)
                for child in self.tree.get_children(item):
                    child_name = self.tree.item(child, 'text')
                    child_path = parent_path + '/' + child_name if parent_path else child_name
                    traverse(child, child_path)

        for root_child in self.tree.get_children(''):
            root_name = self.tree.item(root_child, 'text')
            traverse(root_child, root_name)

        return {p for p in expanded}

    def _expand_path_no_select(self, path: str):
        parts = path.split('/')

        def find(parent, index):
            if index >= len(parts):
                return
            for child in self.tree.get_children(parent):
                if self.tree.item(child, 'text') == parts[index]:
                    self.tree.item(child, open=True)
                    find(child, index + 1)
                    break

        find('', 0)

    def set_translation_checker(self, checker):
        self.translation_checker = checker