import re
import tkinter as tk
import ttkbootstrap as ttkb
from typing import Dict, List

from mcntools.ui.picker import MultiSelectDropdown


class FilteredTreeview(ttkb.Treeview):

    def __init__(self, parent, columns=('文件', '索引', '原文', '译文'), **kwargs):
        super().__init__(parent, columns=columns, show='headings', **kwargs)
        self.filter_texts = {col: '' for col in columns}
        self.original_data = []
        self.current_data = []
        self.sort_column = None
        self.sort_reverse = False
        self.translation_filter_var = tk.StringVar(value='全部')

        self._init_filters()
        self._init_columns()
        self.hide_file_column()
        self.bind('<Control-a>', lambda e: self.selection_set(self.get_children()))

    def _init_filters(self):
        self.filter_frame = ttkb.Frame(self.master)
        self.filter_frame.pack(fill=tk.X, pady=(0, 5))
        self.filter_entries = {}

        frame_file = ttkb.Frame(self.filter_frame)
        frame_file.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttkb.Label(frame_file, text='文件').pack(side=tk.LEFT)
        self.file_picker = MultiSelectDropdown(master=frame_file, values=[], width=12)
        self.file_picker.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.file_picker.bind("<<MultiSelectChanged>>", lambda e: self._on_file_filter_changed())
        self.filter_entries['文件'] = self.file_picker

        for col in ('原文', '译文'):
            frame = ttkb.Frame(self.filter_frame)
            frame.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            ttkb.Label(frame, text=col).pack(side=tk.LEFT)
            entry = ttkb.Entry(frame, width=10)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind('<KeyRelease>', lambda e, c=col: self.on_filter_change(c))
            self.filter_entries[col] = entry

        ttkb.Label(self.filter_frame, text='匹配模式:').pack(side=tk.LEFT, padx=(10, 2))
        self.regex_options = MultiSelectDropdown(self.filter_frame, values=['忽略大小写 (i)', '多行模式 (m)', '点匹配换行 (s)'], width=15)
        self.regex_options.pack(side=tk.LEFT, padx=2)
        self.regex_options.bind("<<MultiSelectChanged>>", lambda e: self.apply_filters())

        ttkb.Label(self.filter_frame, text='状态:').pack(side=tk.LEFT, padx=(10, 2))
        state_combo = ttkb.Combobox(self.filter_frame, textvariable=self.translation_filter_var,
                                    values=['全部', '已翻译', '未翻译'], state='readonly', width=8)
        state_combo.pack(side=tk.LEFT, padx=2)
        state_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())

        ttkb.Button(self.filter_frame, text='清除筛选',
                    command=self.clear_filters).pack(side=tk.RIGHT, padx=5)
    
    def _init_columns(self):
        for col in self['columns']:
            self.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))

    def _on_file_filter_changed(self):
        self.apply_filters()

    def get_regex_flags_list(self) -> List[str]:
        selected = self.regex_options.get_selected()
        flags = []
        for opt in selected:
            if '忽略大小写' in opt:
                flags.append('i')
            elif '多行模式' in opt:
                flags.append('m')
            elif '点匹配换行' in opt:
                flags.append('s')
        return flags

    def set_regex_flags_list(self, flag_list: List[str]) -> None:
        desc_map = {'i': '忽略大小写 (i)', 'm': '多行模式 (m)', 's': '点匹配换行 (s)'}
        values = [desc_map[f] for f in flag_list if f in desc_map]
        self.regex_options.set_selected(values)

    def hide_file_column(self):
        self.column('文件', width=0, stretch=False)

    def show_file_column(self):
        self.column('文件', width=500, stretch=True)

    def on_filter_change(self, col):
        if col in ('原文', '译文'):
            self.filter_texts[col] = self.filter_entries[col].get().strip()
        self.apply_filters()

    def clear_filters(self):
        for col in ('原文', '译文'):
            entry = self.filter_entries.get(col)
            if isinstance(entry, ttkb.Entry):
                entry.delete(0, tk.END)
                self.filter_texts[col] = ''
        self.file_picker.clear()
        self.translation_filter_var.set('全部')
        self.apply_filters()

    def apply_filters(self):
        if not self.original_data:
            self.current_data = []
            self.refresh_display()
            return

        selected_files = set(self.file_picker.get_selected())
        flags = 0
        for flag_char in self.get_regex_flags_list():
            if flag_char == 'i':
                flags |= re.IGNORECASE
            elif flag_char == 'm':
                flags |= re.MULTILINE
            elif flag_char == 's':
                flags |= re.DOTALL

        filtered_data = []
        for item in self.original_data:
            file_path = item.get('_file', '')
            if file_path and file_path not in selected_files:
                continue

            show = True
            for col in ('原文', '译文'):
                pattern = self.filter_texts.get(col, '')
                if pattern:
                    try:
                        if not re.search(pattern, str(item.get(col, '')), flags):
                            show = False
                            break
                    except re.error:
                        pass
            if not show:
                continue

            trans = item.get('译文', '')
            orig = item.get('原文', '')
            status = self.translation_filter_var.get()
            if status == '已翻译':
                if not trans or trans == orig:
                    continue
            elif status == '未翻译':
                if trans and trans != orig:
                    continue

            filtered_data.append(item)

        self.current_data = filtered_data
        self.refresh_display()

    def clear_items(self):
        self.delete(*self.get_children())

    def _save_selection(self) -> List[Dict]:
        return self.get_selected_items_data()

    def _restore_selection(self, saved_items: List[Dict]):
        if not saved_items:
            return
        for item in saved_items:
            for idx, current_item in enumerate(self.current_data):
                if (current_item.get('_file') == item.get('_file') and
                        current_item.get('原文') == item.get('原文')):
                    iid = next((iid for iid in self.get_children() 
                               if int(self.item(iid, 'tags')[0]) == idx), None)
                    if iid:
                        self.selection_add(iid)

    def _get_offset_color(self, hex_color: str, offset=10):
        """对颜色进行智能偏移（根据亮度自动调整方向）"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c * 2 for c in hex_color])
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        delta = (-1 if brightness > 128 else 1) * offset
        r = max(0, min(255, r + delta))
        g = max(0, min(255, g + delta))
        b = max(0, min(255, b + delta))
        return f'#{r:02x}{g:02x}{b:02x}'

    def apply_zebra_stripes(self):
        """配置表格斑马纹"""
        style = ttkb.Style()
        bg = style.lookup('Treeview', 'background')
        self.tag_configure('oddrow', background=self._get_offset_color(bg))
        self.tag_configure('evenrow', background=bg)
        return self

    def refresh_display(self):
        saved_items = self._save_selection()
        self.clear_items()
        for idx, item in enumerate(self.current_data):
            vals = [item.get(col, '') for col in self['columns']]
            tag = 'oddrow' if idx % 2 == 0 else 'evenrow'
            self.insert('', 'end', values=vals, tags=(str(idx), tag))
        self._restore_selection(saved_items)

    def set_data(self, data: List[Dict]):
        self.original_data = data.copy()
        self.current_data = data.copy()
        all_files = sorted({d['_file'] for d in data if d.get('_file')})
        self.file_picker.set_values(all_files)
        self.file_picker.select_all()
        self.apply_filters()

    def set_filter_texts(self, filter_texts_dict: Dict[str, str]):
        for col in ('原文', '译文'):
            if col in filter_texts_dict:
                text = filter_texts_dict[col]
                self.filter_texts[col] = text
                entry = self.filter_entries.get(col)
                if isinstance(entry, ttkb.Entry):
                    entry.delete(0, tk.END)
                    entry.insert(0, text)
        self.apply_filters()

    def get_filter_texts(self) -> Dict[str, str]:
        return {col: self.filter_texts.get(col, '') for col in ('原文', '译文')}

    def get_selected_items_data(self) -> List[Dict]:
        data = []
        for iid in self.selection():
            tags = self.item(iid, 'tags')
            if tags:
                idx = int(tags[0])
                if idx < len(self.current_data):
                    data.append(self.current_data[idx])
        return data

    def sort_by_column(self, col):
        if not self.current_data:
            return
        self.sort_reverse = not self.sort_reverse if self.sort_column == col else False
        self.sort_column = col
        self.current_data.sort(
            key=lambda item: str(item.get(col, '')).lower() if col != '索引' else int(item.get(col, 0)),
            reverse=self.sort_reverse
        )
        self.refresh_display()