import json
import os
import re
import threading
import tkinter as tk
import ttkbootstrap as ttkb
from tkinter import filedialog
from ttkbootstrap.widgets.scrolled import ScrolledText
from ttkbootstrap.dialogs import Messagebox
from typing import Dict

from mcntools.config import BACKUP_EXT, CONFIG_FILE, FONT_DEFAULT, FONT_FAMILY, LANGUAGES, ENGINES
from mcntools.core import TranslationService, WorkspaceManager
from mcntools.translators import TranslatorFactory
from mcntools.ui import WorkspaceTree, FilteredTreeview
from mcntools.ui.preview import FilePreview

DEFAULT_CONFIG = {
    "theme": "darkly",
    "window_state": "normal",
    "normal_geometry": "1400x800",
    "show_backup": False,
    "wrap_text": True,
    "regex_flags": [],
    "filter_texts": {},
    "target_lang": "zh",
    "engine": "google",
    "api_config": {}
}

class JARClassTranslator:

    def __init__(self, root):
        self.root = root
        self.root.title("JAR 硬编码翻译工具")

        self.config = self._load_config()
        self._apply_theme()
        self._init_services()

        target_lang_code = self.config.get('target_lang', DEFAULT_CONFIG['target_lang'])
        target_lang_display = f"{target_lang_code} - {LANGUAGES.get(target_lang_code)}"
        self.target_lang_var = tk.StringVar(value=target_lang_display)
        self.lang_display_dict = {f"{k} - {v}": k for k, v in LANGUAGES.items() if k != 'auto'}
        
        self.current_engine = self.config.get('engine', DEFAULT_CONFIG['engine'])
        self.engine_var = tk.StringVar(value=self._get_engine_display(self.current_engine))
        self.translator = self._create_translator(self.current_engine)

        self._init_ui()
        self._restore_state()
        self._bind_shortcuts()
        self._update_translator_status()

    def _get_api_key(self, engine: str) -> str:
        return self.config.get('api_config', {}).get(engine, {}).get('api_key', '')
    
    def _get_engine_display(self, engine: str) -> str:
        engine_info = ENGINES.get(engine, {})
        return f"{engine_info.get('icon', '')} {engine_info.get('name', engine)}"

    def _create_translator(self, engine: str):
        to_display = self.target_lang_var.get()
        to_code = to_display.split(' - ')[0] if ' - ' in to_display else to_display
        return TranslatorFactory.create(engine, self._get_api_key(engine), 'auto', to_code)

    def _init_services(self):
        self.workspace_manager = WorkspaceManager()
        self.service = TranslationService(self.workspace_manager)

        self.current_jar_id = None
        self.current_path = None

        self.current_item = None
        self.current_preview_file = None
        self.folder_mode = False
        self.current_folder = None
        self.saved_class_path = None
        self._resize_timer = None

    def _load_config(self) -> Dict:
        default_config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"加载配置失败: {e}")
        return default_config

    def _save_config(self):
        state = self.root.state()
        if state == 'normal':
            normal_geometry = self.root.geometry()
        else:
            normal_geometry = self.config.get('normal_geometry', DEFAULT_CONFIG['normal_geometry'])

        to_display = self.target_lang_var.get()
        to_code = to_display.split(' - ')[0] if ' - ' in to_display else to_display        
        config = {
            "theme": self.theme_var.get(),
            "window_state": state,
            "normal_geometry": normal_geometry,
            "show_backup": self.workspace_tree.show_backup,
            "wrap_text": self.word_wrap_var.get(),
            "regex_flags": self.const_tree.get_regex_flags_list(),
            "filter_texts": self.const_tree.get_filter_texts(),
            "api_config": self.config.get('api_config', {}),
            "target_lang": to_code,
            "engine": self.current_engine
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _apply_theme(self):
        self.current_theme = self.config.get("theme", DEFAULT_CONFIG['theme'])
        self.theme_var = tk.StringVar(value=self.current_theme)
        ttkb.Style().theme_use(self.current_theme)
        if getattr(self, 'const_tree', None):
            self.const_tree.apply_zebra_stripes()

        normal_geometry = self.config.get("normal_geometry", DEFAULT_CONFIG['normal_geometry'])
        self.root.geometry(normal_geometry)
        if self.config.get("window_state") == "zoomed":
            self.root.state("zoomed")
        self.root.minsize(1000, 600)

    def _restore_state(self):
        self.workspace_tree.show_backup = self.config.get("show_backup", DEFAULT_CONFIG['show_backup'])
        self.backup_var.set(self.workspace_tree.show_backup)
        self.word_wrap_var.set(self.config.get("wrap_text", DEFAULT_CONFIG['wrap_text']))
        self._toggle_word_wrap()

        saved_regex_flags = self.config.get("regex_flags", DEFAULT_CONFIG['regex_flags'])
        self.const_tree.set_regex_flags_list(saved_regex_flags)

        saved_filter_texts = self.config.get("filter_texts", DEFAULT_CONFIG['filter_texts'])
        if saved_filter_texts:
            self.const_tree.set_filter_texts(saved_filter_texts)

        target_lang_code = self.config.get("target_lang", DEFAULT_CONFIG['target_lang'])
        target_lang_display = f"{target_lang_code} - {LANGUAGES.get(target_lang_code, target_lang_code)}"
        self.target_lang_var.set(target_lang_display)

        engine = self.config.get("engine", DEFAULT_CONFIG['engine'])
        self.current_engine = engine
        engine_display = self._get_engine_display(engine)
        self.engine_var.set(engine_display)

    def _init_menu(self):
        menubar = tk.Menu(self.root)
        self.root['menu'] = menubar

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开 JAR", accelerator="Ctrl+O", command=self.open_jar)
        file_menu.add_command(label="保存 JAR", accelerator="Ctrl+S", command=self.save_jar)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.destroy)

        trans_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="翻译", menu=trans_menu)

        engine_menu = tk.Menu(trans_menu, tearoff=0)
        trans_menu.add_cascade(label="翻译引擎", menu=engine_menu)
        for engine_id, info in ENGINES.items():
            display_value = f"{info['icon']} {info['name']}"
            engine_menu.add_radiobutton(
                label=display_value,
                variable=self.engine_var,
                value=display_value,
                command=self._on_engine_change
            )

        lang_menu = tk.Menu(trans_menu, tearoff=0)
        trans_menu.add_cascade(label="目标语言", menu=lang_menu)

        for display_value in self.lang_display_dict.keys():
            lang_menu.add_radiobutton(
                label=display_value,
                variable=self.target_lang_var,
                value=display_value,
                command=self._on_language_change
            )

        trans_menu.add_separator()
        trans_menu.add_command(label="配置DeepSeek", command=self._show_api_config_dialog)

        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="主题", menu=theme_menu)
        themes = {
            'sandstone': '浅色 - 砂岩橙',
            'united': '浅色 - 炽烈橙',
            'journal': '浅色 - 纸笺黄',
            'minty': '浅色 - 薄荷绿',
            'flatly': '浅色 - 扁平绿',
            'cosmo': '浅色 - 星际蓝',
            'lumen': '浅色 - 流光蓝',
            'yeti': '浅色 - 雪域蓝',
            'pulse': '浅色 - 脉动蓝',
            'morph': '浅色 - 灵动蓝',
            'litera': '浅色 - 书卷灰',
            'simplex': '浅色 - 素简灰',
            'cyborg': '深色 - 赛博黑',
            'darkly': '深色 - 暗夜灰',
            'vapor': '深色 - 蒸汽紫',
            'superhero': '深色 - 漫威蓝',
            'solar': '深色 - 日蚀黄',
        }
        for theme, label in themes.items():
            theme_menu.add_radiobutton(label=label, variable=self.theme_var, value=theme, command=self._change_theme)

        self._update_menu_colors(menubar)
        self.menubar = menubar

    def _update_menu_colors(self, menubar):
        style = ttkb.Style()
        try:
            bg = style.lookup('TMenu', 'background')
            fg = style.lookup('TMenu', 'foreground')
        except:
            bg, fg = None, None
        dark_themes = {'darkly', 'superhero', 'solar', 'cyborg', 'vapor'}
        is_dark = self.theme_var.get() in dark_themes
        if not bg:
            bg = '#2b2b2b' if is_dark else '#ffffff'
        if not fg:
            fg = '#ffffff' if is_dark else '#000000'
        menubar.config(bg=bg, fg=fg)
        for menu in menubar.winfo_children():
            if isinstance(menu, tk.Menu):
                menu.config(bg=bg, fg=fg)
                for submenu in menu.winfo_children():
                    if isinstance(submenu, tk.Menu):
                        submenu.config(bg=bg, fg=fg)

    def _update_workspace_menu_colors(self):
        style = ttkb.Style()
        bg = style.lookup('TFrame', 'background')
        fg = style.lookup('TLabel', 'foreground')
        
        menus = [
            self.workspace_tree.file_context_menu,
            self.workspace_tree.folder_context_menu
        ]
        
        for menu in menus:
            menu.config(bg=bg, fg=fg)
            for submenu in menu.winfo_children():
                if isinstance(submenu, tk.Menu):
                    submenu.config(bg=bg, fg=fg)

    def _change_theme(self):
        self.current_theme = self.theme_var.get()
        
        style = ttkb.Style()
        style.theme_use(self.current_theme)
        
        if getattr(self, 'menubar', None):
            self._update_menu_colors(self.menubar)
        if getattr(self, 'workspace_tree', None):
            self._update_workspace_menu_colors()
            
        self.root.update_idletasks()
        self.root.update()
        if getattr(self, 'const_tree', None):
            self.const_tree.apply_zebra_stripes().refresh_display()
        if getattr(self, 'preview', None):
            self.preview.apply_theme()

    def _toggle_word_wrap(self):
        self.preview.set_wrap(self.word_wrap_var.get())

    def _bind_shortcuts(self):
        self.root.bind('<Control-o>', lambda e: self.open_jar())
        self.root.bind('<Control-s>', lambda e: self.save_jar())
        self.root.bind('<Control-t>', lambda e: self._translate_selected())

    def _init_ui(self):
        self._init_menu()

        main_paned = ttkb.Panedwindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttkb.Frame(main_paned, padding=5)
        main_paned.add(left_frame, weight=1)

        left_header = ttkb.Frame(left_frame)
        left_header.pack(fill=tk.X, pady=(0, 5))
        ttkb.Label(left_header, text="工作空间", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        self.backup_var = tk.BooleanVar(value=False)

        self.workspace_tree = WorkspaceTree(
            left_frame,
            on_file_select=self._on_file_select,
            on_folder_select=self._on_folder_select,
            on_rename=self._on_rename_file,
            on_backup=self._on_backup_file,
            on_save_jar=self.save_jar,
            backup_var=self.backup_var
        )

        self.backup_check = ttkb.Checkbutton(
            left_header, text="显示备份", 
            variable=self.backup_var,
            command=self.workspace_tree.toggle_backup_visibility)
        self.backup_check.pack(side=tk.RIGHT)
        self.workspace_tree.pack(fill=tk.BOTH, expand=True)
        self.workspace_tree.set_translation_checker(self._has_translations)

        right_container = ttkb.Frame(main_paned)
        main_paned.add(right_container, weight=10)

        toolbar = ttkb.Frame(right_container)
        toolbar.pack(fill=tk.X, pady=5)

        self.filter_label = ttkb.Label(toolbar, text="总计: 0 条字符串", foreground="gray")
        self.filter_label.pack(side=tk.LEFT, padx=5)

        path_frame = ttkb.Frame(right_container)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        ttkb.Label(path_frame, text="路径:").pack(side=tk.LEFT, padx=5)
        self.path_label = ttkb.Label(path_frame, text="", foreground="#0d6efd")
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.content_frame = ttkb.Frame(right_container)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self._init_class_mode()

        self._init_preview_mode()

        self._set_view_mode('class')

        self.status = ttkb.Label(
            self.root,
            text="就绪 | Ctrl+T 翻译选中",
            anchor=tk.W,
            padding=(10, 5)
        )
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.after(100, self._set_pane_ratio)
        self.root.bind('<Configure>', self._on_window_resize)

    def _init_class_mode(self):
        self.class_paned = ttkb.Panedwindow(self.content_frame, orient=tk.VERTICAL)

        const_frame = ttkb.LabelFrame(self.class_paned, text="字符串")
        self.class_paned.add(const_frame, weight=1)

        tree_container = ttkb.Frame(const_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('文件', '索引', '原文', '译文')
        self.const_tree = FilteredTreeview(tree_container, columns=columns, height=15).apply_zebra_stripes()
        self.const_tree.heading('文件', text='文件')
        self.const_tree.heading('索引', text='索引')
        self.const_tree.heading('原文', text='原文')
        self.const_tree.heading('译文', text='译文')
        self.const_tree.column('索引', width=55, anchor='center', stretch=False)
        self.const_tree.column('原文', width=400)
        self.const_tree.column('译文', width=400)

        scroll_x = ttkb.Scrollbar(tree_container, orient="horizontal", command=self.const_tree.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y = ttkb.Scrollbar(tree_container, orient="vertical", command=self.const_tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.const_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.const_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.const_tree.bind('<<TreeviewSelect>>', self._on_const_select)

        edit_frame = ttkb.LabelFrame(self.class_paned, text="编辑")
        self.class_paned.add(edit_frame, weight=1)

        edit_paned = ttkb.Panedwindow(edit_frame, orient=tk.HORIZONTAL)
        edit_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        orig_frame = ttkb.Frame(edit_paned)
        edit_paned.add(orig_frame, weight=1)
        ttkb.Label(orig_frame, text="原文:").pack(anchor=tk.W)
        self.original_text = ScrolledText(orig_frame, wrap=tk.WORD, font=FONT_DEFAULT, height=3, autohide=False)
        self.original_text.pack(fill=tk.BOTH, expand=True)

        trans_frame = ttkb.Frame(edit_paned)
        edit_paned.add(trans_frame, weight=1)
        ttkb.Label(trans_frame, text="译文:").pack(anchor=tk.W)
        self.translation_text = ScrolledText(trans_frame, wrap=tk.WORD, font=FONT_DEFAULT, height=3, autohide=False)
        self.translation_text.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttkb.Frame(edit_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.translate_btn = ttkb.Button(btn_frame, text="🌐 翻译原文", bootstyle="info", command=self._translate_selected)
        self.clear_btn = ttkb.Button(btn_frame, text="❌ 删除译文", bootstyle="danger", command=self._delete_translation)
        self.apply_btn = ttkb.Button(btn_frame, text="💾 保存译文", bootstyle="success", command=self._apply_translation)
        self.translate_btn.pack(side=tk.LEFT, padx=2)
        self.clear_btn.pack(side=tk.LEFT, padx=2)
        self.apply_btn.pack(side=tk.LEFT, padx=2)

        engine_frame = ttkb.Frame(btn_frame)
        engine_frame.pack(side=tk.RIGHT, padx=10)
        ttkb.Label(engine_frame, text="引擎").pack(side=tk.LEFT)
        self.engine_combo = ttkb.Combobox(
            engine_frame, textvariable=self.engine_var,
            values=[f"{info.get('icon', '')} {info.get('name', '')}" for info in ENGINES.values()],
            state='readonly', width=15)
        self.engine_combo.pack(side=tk.LEFT, padx=2)
        self.engine_combo.bind('<<ComboboxSelected>>', lambda e: (self._on_engine_change(e), self.engine_combo.selection_clear()))

        lang_frame = ttkb.Frame(btn_frame)
        lang_frame.pack(side=tk.RIGHT)
        ttkb.Label(lang_frame, text="目标语言").pack(side=tk.LEFT, padx=(0, 2))
        target_combo = ttkb.Combobox(
            lang_frame, textvariable=self.target_lang_var, state='readonly', width=12,
            values=list(self.lang_display_dict.keys()))
        target_combo.pack(side=tk.LEFT, padx=2)
        target_combo.bind('<<ComboboxSelected>>', lambda e: (self._on_language_change(), target_combo.selection_clear()))

    def _on_language_change(self):
        to_display = self.target_lang_var.get()
        to_code = self.lang_display_dict.get(to_display, self.config.get('target_lang'))
        if to_code and to_code != self.translator.to_code:
            self.translator.to_code = to_code
            self._save_config()
            self.update_status(f"目标语言已切换为: {LANGUAGES.get(to_code, to_code)}")

    def _on_engine_change(self, event=None):
        engine_display = self.engine_var.get()
        engine_key = None
        for key, info in ENGINES.items():
            display = self._get_engine_display(key)
            if display == engine_display:
                engine_key = key
                break
        
        if engine_key is None:
            engine_key = engine_display
        
        if engine_key == self.current_engine:
            return

        self.current_engine = engine_key
        self._save_config()
        self.translator = self._create_translator(engine_key)

        self._update_translator_status()
        info = ENGINES.get(engine_key, {})
        self.update_status(f"已切换到 {info.get('name', engine_key)}")

    def _update_translator_status(self):
        status = self.translator.get_status()
        if hasattr(self, 'engine_combo'):
            if status['available']:
                self.engine_combo.config(bootstyle="success")
                self.translate_btn.config(state="normal")
            else:
                self.engine_combo.config(bootstyle="danger")
                self.translate_btn.config(state="disabled")

    def _show_api_config_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("配置DeepSeek")
        dialog.geometry("600x340")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 340) // 2
        dialog.geometry(f"+{x}+{y}")

        frame = ttkb.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttkb.Label(frame, text="DeepSeek API", font=(FONT_FAMILY, 14, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        engine = 'deepseek'

        link_frame = ttkb.Frame(frame)
        link_frame.pack(anchor=tk.W, pady=(0, 10))
        ttkb.Label(frame, text="API Key:").pack(anchor=tk.W, pady=(10, 2))
        key_entry = ttkb.Entry(frame, width=50, show="*")
        key_entry.pack(fill=tk.X, pady=(0, 5))
        key_entry.insert(0, self._get_api_key(engine))

        show_frame = ttkb.Frame(frame)
        show_frame.pack(anchor=tk.W, pady=(0, 10))
        show_var = tk.BooleanVar(value=False)
        ttkb.Checkbutton(
            show_frame, text="显示API Key",
            variable=show_var,
            command=lambda: key_entry.config(show="" if show_var.get() else "*")
        ).pack(side=tk.LEFT)

        btn_frame = ttkb.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttkb.Button(
            btn_frame, text="💾 保存", bootstyle="success",
            command=lambda: self._save_api_config({engine: key_entry.get().strip()}, dialog)
        ).pack(side=tk.RIGHT, padx=5)
        ttkb.Button(
            btn_frame, text="❌ 取消", bootstyle="secondary",
            command=dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def _save_api_config(self, api_keys: dict, dialog: tk.Toplevel):
        api_config = self.config.get('api_config', {})
        for engine, api_key in api_keys.items():
            api_config.update({engine: {"api_key": api_key}})
            if self.translator and self.translator.engine == engine:
                self.translator.set_api_key(api_key)
        self.config.update({'api_config': api_config})
        self._update_translator_status()
        self._save_config()
        dialog.destroy()

    def _init_preview_mode(self):
        self.preview_frame = ttkb.LabelFrame(self.content_frame, text="文件预览")

        preview_toolbar = ttkb.Frame(self.preview_frame)
        preview_toolbar.pack(fill=tk.X, pady=(5, 5), padx=5)
        self.word_wrap_var = tk.BooleanVar(value=False)
        self.wrap_check = ttkb.Checkbutton(
            preview_toolbar, text="自动换行",
            variable=self.word_wrap_var,
            command=self._toggle_word_wrap
        )
        self.wrap_check.pack(side=tk.LEFT, padx=5)
        ttkb.Button(preview_toolbar, text="保存修改", bootstyle="primary",
                   command=self._save_preview).pack(side=tk.LEFT, padx=5)

        self.preview = FilePreview(self.preview_frame, font=FONT_DEFAULT)
        self.preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    def _set_view_mode(self, mode: str):
        if mode == 'class':
            self.class_paned.pack(fill=tk.BOTH, expand=True)
            self.preview_frame.pack_forget()
        else:
            self.class_paned.pack_forget()
            self.preview_frame.pack(fill=tk.BOTH, expand=True)

    def _set_pane_ratio(self):
        width = self.root.winfo_width()
        if width > 200:
            self.root.children['!panedwindow'].sashpos(0, int(width * 0.25))

    def _on_window_resize(self, event):
        if event.widget == self.root:
            if self._resize_timer:
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(150, self._set_pane_ratio)

    def update_status(self, msg: str):
        self.status.config(text=msg)

    def _has_translations(self, jar_id: str, path: str) -> bool:
        return self.service.has_translations(jar_id, path)

    def _on_rename_file(self, jar_id: str, old_path: str, new_path: str) -> bool:
        return self.service.rename_file(jar_id, old_path, new_path)

    def _on_backup_file(self, jar_id: str, path: str) -> bool:
        result = self.service.create_backup(jar_id, path)
        if result:
            entry = self.workspace_manager.get_entry(jar_id)
            if entry:
                backup_path = path + BACKUP_EXT
                if backup_path in entry.jar_handler.files:
                    self.workspace_tree.files[jar_id][backup_path] = entry.jar_handler.files[backup_path]
            self.workspace_tree.rebuild_tree()
            self.update_status(f"已创建备份: {path}{BACKUP_EXT}")
        else:
            self.update_status(f"创建备份失败: {path}")
        return result

    def _on_folder_select(self, jar_id: str, paths: list, extract: bool = False):
        self.current_jar_id = jar_id
        self.folder_mode = True
        self.current_folder = os.path.dirname(paths[0]) if paths else None

        if extract:
            self.service.extract_strings_from_classes(jar_id, paths)
            self.update_status(f"已提取 {len(paths)} 个class文件的字符串到映射表")
        else:
            self.update_status(f"预览 {len(paths)} 个class文件的字符串")

        self._show_folder_strings(jar_id, self.current_folder)

    def _on_file_select(self, jar_id: str, path: str):
        if not path:
            return
        
        self.current_jar_id = jar_id
        self.current_preview_file = path

        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return

        if entry.jar_handler.is_directory(path):
            self.folder_mode = True
            self.current_folder = path
            self._set_view_mode('class')
            class_count = len(entry.jar_handler.get_class_files(path))
            self.filter_label.config(text=f"文件夹: {path} — {class_count} 个class文件 (右键预览/提取)")
        elif re.search(r'\.class(\.bak)?$', path):
            self.folder_mode = False
            self.current_folder = None
            self._set_view_mode('class')
            self._preview_class(jar_id, path)
        else:
            self.folder_mode = False
            self.current_folder = None
            self._set_view_mode('preview')
            self._preview_text(jar_id, path)

    def _show_folder_strings(self, jar_id: str, folder_path: str):
        if not self.service:
            return

        items = self.service.get_folder_strings(jar_id, folder_path, extract=False)
        data = [item.to_dict() for item in items]

        self.const_tree.show_file_column()
        self.const_tree.set_data(data)
        self.filter_label.config(text=f"文件夹: {folder_path} — {len(data)} 条字符串")
        self.path_label.config(text=f"{jar_id}/{folder_path}")
        self._set_edit_mode()

    def _preview_text(self, jar_id: str, path: str):
        self.path_label.config(text=f"{jar_id}/{path}")
        
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            self.preview.show_error(f"无法找到JAR文件: {jar_id}")
            return
            
        content = entry.jar_handler.read_file(path)
        if not content:
            self.preview.show_error(f"无法读取文件: {path}")
            self.update_status(f"无法读取文件: {path}")
            return
        try:
            self.preview.set_content(path, content)
            self.update_status(f"已预览: {os.path.basename(path)} ({len(content)} 字节)")
        except Exception as e:
            self.preview.show_error(f"预览失败: {str(e)}")
            self.update_status(f"预览失败: {e}")

    def _preview_class(self, jar_id: str, path: str):
        is_bak = path.endswith(BACKUP_EXT)
        file_path = path[:-4] if is_bak else path
        self.current_path = file_path
        self.current_jar_id = jar_id

        self.const_tree.hide_file_column()
        self.const_tree.set_data([])
        self._clear_text()
        self.current_item = None
        self.path_label.config(text=f"{jar_id}/{path}")
        self.update_status(f"分析: {path}...")
        self._analyze_class()

    def _analyze_class(self):
        if not self.service or not self.current_path or not self.current_jar_id:
            return

        try:
            items = self.service.get_class_strings(self.current_jar_id, self.current_path)
            data = [item.to_dict() for item in items]
            self.const_tree.set_data(data)
            self.filter_label.config(text=f"总计: {len(data)} 条字符串")
            self.update_status(f"分析完成: {self.current_path}")
        except Exception as e:
            self.update_status(f"加载失败: {e}")

    def _refresh_display(self):
        if self.current_path:
            self._analyze_class()

    def _on_const_select(self, event):
        sel = self.const_tree.selection()
        if not sel:
            self._set_edit_mode()
            self.path_label.config(text=self.current_preview_file if self.current_preview_file else "")
            return

        if len(sel) == 1:
            self._set_edit_mode()
            data_list = self.const_tree.get_selected_items_data()
            if data_list:
                item = data_list[0]
                file_path = item['_file']
                original = item['_original']
                translation = item['译文'].replace('\\n', '\n').replace('\\r', '\r') or original
                self._set_text(original, translation)
                self.current_item = (file_path, original, translation)
                self.path_label.config(text=file_path)
        else:
            self._set_edit_mode(len(sel))
            self.current_item = None
            data_list = self.const_tree.get_selected_items_data()
            files = list({item['_file'] for item in data_list if item.get('_file')})
            self.path_label.config(text="; ".join(files) if files else "")

    def _set_edit_mode(self, batch_count: int = 0):
        if batch_count > 0:
            self.apply_btn.pack_forget()
            self._clear_text()
            self.translate_btn.config(text=f"🌐 翻译原文 ({batch_count})")
            self.clear_btn.config(text=f"❌ 删除译文 ({batch_count})")
        else:
            self.translate_btn.config(text="🌐 翻译原文")
            self.clear_btn.config(text="❌ 删除译文")
            self.apply_btn.pack(side=tk.LEFT, padx=2)

    def _set_text(self, original_text: str = None, translation_text: str = None):
        if original_text:
            self.original_text.text.config(state=tk.NORMAL)
            self.original_text.text.delete(1.0, tk.END)
            self.original_text.text.insert(1.0, original_text)
            self.original_text.text.config(state=tk.DISABLED)
        if translation_text:
            self.translation_text.text.delete(1.0, tk.END)
            self.translation_text.text.insert(1.0, translation_text)

    def _clear_text(self):
        self.original_text.text.config(state=tk.NORMAL)
        self.original_text.text.delete(1.0, tk.END)
        self.original_text.text.config(state=tk.DISABLED)
        self.translation_text.text.delete(1.0, tk.END)

    def _set_buttons_state(self, state: str):
        for btn in (self.translate_btn, self.clear_btn, self.apply_btn):
            btn.config(state=state)

    def _can_edit_translation(self) -> bool:
        return self.current_item is not None and self.service is not None

    def _refresh_current_view(self):
        if self.folder_mode:
            self._show_folder_strings(self.current_jar_id, self.current_folder)
        elif self.current_path:
            self._refresh_display()
        self.workspace_tree.rebuild_tree()

    def _apply_translation(self):
        if not self._can_edit_translation():
            self.update_status("请先在常量池中选择一个字符串")
            return

        file_path, original, _ = self.current_item
        translation = self.translation_text.get(1.0, tk.END).rstrip('\n')
        if not translation:
            self.update_status("译文不能为空")
            return

        self.service.update_translation(self.current_jar_id, file_path, original, translation)
        self._refresh_current_view()
        self.update_status(f"已应用翻译: {original[:30]}...")

    def _delete_translation(self):
        data_list = self.const_tree.get_selected_items_data()
        if not data_list:
            self.update_status("请先选中要删除的翻译项")
            return

        if len(data_list) > 1:
            if not Messagebox.yesno(f"确定要删除选中的 {len(data_list)} 条翻译吗？", "批量删除"):
                return
        else:
            if not self._can_edit_translation():
                return

        self.service.batch_delete_translations(self.current_jar_id, data_list)

        if len(data_list) == 1:
            path, original = data_list[0]['_file'], data_list[0]['_original']
            self._set_text(translation_text=original)
            self.current_item = (path, original, original)

        self._refresh_current_view()
        self.update_status(f"已批量删除 {len(data_list)} 条翻译")

    def _normalize_newlines(self, text: str) -> str:
        if not text:
            return text
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        while text.endswith('\n'):
            text = text[:-1]
        return text

    def _save_preview(self):
        if not self.current_preview_file:
            return

        content = self.preview.get_text()
        if content is None:
            self.update_status("当前预览模式无可保存的文本内容")
            return
        content = self._normalize_newlines(content)

        if self.current_preview_file.endswith('.json'):
            self._save_json(content)
        else:
            self._save_text(content)

        self._preview_text(self.current_jar_id, self.current_preview_file)

    def _save_json(self, content: str):
        try:
            data = json.loads(content)
            
            entry = self.workspace_manager.get_entry(self.current_jar_id)
            if not entry:
                Messagebox.show_error(f"无法找到JAR文件: {self.current_jar_id}", "保存失败")
                return
            
            entry.jar_handler.write_file(self.current_preview_file, json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8'))
            self.update_status(f"已保存 JSON: {self.current_preview_file}")

            jar_name = entry.jar_path.split(os.sep)[-1]
            expected_json = f"{jar_name}.json"
            if self.current_preview_file == expected_json and self.service:
                self._apply_json_to_classes(self.current_jar_id, data)
                self.workspace_tree.rebuild_tree()
        except json.JSONDecodeError as e:
            Messagebox.show_error(f"JSON 解析失败:\n{str(e)}", "JSON 格式错误")
        except Exception as e:
            Messagebox.show_error(f"保存 JSON 失败:\n{str(e)}", "保存失败")

    def _apply_json_to_classes(self, jar_id: str, data: Dict):
        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            return
            
        count = 0
        for path in entry.class_processor.get_all_paths():
            info = entry.class_processor.get_class_info(path)
            info.translations = data.get(path, {})
            if info.translations:
                if not info.has_backup and info.has_original:
                    entry.backup_manager.create_backup(path)
                    info.has_backup = True
            else:
                if info.has_backup and info.has_original:
                    entry.backup_manager.rename_file(info.bak_path, info.path)
                    info.has_backup = False
            applied = self.service.apply_translations_to_class(jar_id, path)
            count += applied
        entry.translation_manager._dirty = True
        entry.translation_manager.save_translations()
        self.update_status(f"已应用 {count} 条翻译到 class 文件")
        if self.current_path:
            self._refresh_display()

    def _save_text(self, content: str):
        try:
            entry = self.workspace_manager.get_entry(self.current_jar_id)
            if not entry:
                Messagebox.show_error(f"无法找到JAR文件: {self.current_jar_id}", "保存失败")
                return
                
            entry.jar_handler.write_file(self.current_preview_file, content.encode('utf-8'))
            self.update_status(f"已保存: {self.current_preview_file}")
        except UnicodeEncodeError:
            entry.jar_handler.write_file(self.current_preview_file, content.encode('utf-8', errors='ignore'))
            self.update_status(f"已保存(部分字符丢失): {self.current_preview_file}")
        except Exception as e:
            Messagebox.show_error(f"保存文件失败:\n{str(e)}", "保存失败")

    def _translate_selected(self):
        data_list = self.const_tree.get_selected_items_data()
        if not data_list:
            self.update_status("请先选中要翻译的字符串")
            return
        if self.current_engine == 'deepseek' and not self.translator.api_key:
            self.update_status("请先配置DeepSeek")
            return

        to_translate = [item['原文'] for item in data_list]
        engine_info = ENGINES.get(self.current_engine, {})
        self.update_status(f"正在使用 {engine_info.get('name', '翻译器')} 翻译 {len(to_translate)} 条...")

        self._set_buttons_state('disabled')

        def translate_task():
            try:
                return self.translator.translate(to_translate)
            except Exception as e:
                print(f"翻译失败: {e}")
                return {}

        def on_done(translations):
            self._set_buttons_state('normal')

            if not translations:
                self.update_status("❌ 翻译失败")
                return
            self.service.batch_update_translations(self.current_jar_id, data_list, translations)

            if len(data_list) == 1:
                item = data_list[0]
                original = item.get('原文', '')
                translated = translations.get(original, '')
                if translated and translated != original:
                    self._set_text(translation_text=translated)
                    file_path = item.get('_file', '')
                    self.current_item = (file_path, original, translated)

            self._refresh_current_view()
            self.update_status(f"✅ 翻译完成: {len(to_translate)} 条")

        thread = threading.Thread(target=lambda: self.root.after(0, lambda: on_done(translate_task())))
        thread.daemon = True
        thread.start()

    def open_jar(self):
        paths = filedialog.askopenfilenames(filetypes=[("JAR files", "*.jar")])
        if not paths:
            return

        self.update_status(f"发现 {len(paths)} 个JAR文件，正在加载...")

        for path in paths:
            jar_name = os.path.basename(path)
            self.update_status(f"加载: {jar_name}...")

            entry = self.workspace_manager.add_jar(path)
            self.workspace_tree.add_jar_node(entry.jar_id, entry.jar_name, entry.files)
            
            self.update_status(f"加载完成: {len(entry.files)} 个文件")

        self.update_status(f"全部加载完成，共 {len(paths)} 个JAR文件")

    def save_jar(self, jar_id: str = None):
        if jar_id is None:
            selected = self.workspace_tree.get_selected_path()
            if selected:
                jar_id = selected[0]
            else:
                entries = self.workspace_manager.get_all_entries()
                if entries:
                    jar_id = entries[0].jar_id
                else:
                    Messagebox.show_info("没有可保存的JAR文件", "提示")
                    return

        entry = self.workspace_manager.get_entry(jar_id)
        if not entry:
            Messagebox.show_error(f"未找到JAR文件: {jar_id}", "保存失败")
            return

        self.service.apply_all_translations(jar_id)
        self.update_status("已应用所有翻译")
        self.service.save_jar(jar_id)
        self.update_status(f"已保存 JAR 文件：{entry.jar_path}")

    def _cleanup(self):
        self.service.cleanup()

    def on_closing(self):
        self._save_config()
        self._cleanup()
        self.root.destroy()