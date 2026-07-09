import re
import tkinter as tk
import ttkbootstrap as ttkb
from typing import Dict, List, Callable

from mcntools.ui.picker import MultiCombobox


class FilteredTreeview(ttkb.Treeview):
    """带筛选功能的表格组件，支持列宽按比例自适应"""
    COLUMNS = {
        'path': {'label': '文件', 'stretch': True, 'type': 'text', 'filter': 'multiselect'},
        'index': {'label': '索引', 'width': 55, 'stretch': False, 'type': 'number', 'anchor': 'center'},
        'original': {'label': '原文', 'stretch': True, 'type': 'text', 'filter': 'regex'},
        'translation': {'label': '译文', 'stretch': True, 'type': 'text', 'filter': 'regex'},
    }
    
    def __init__(self, parent, on_select: Callable = None, **kwargs):
        self._on_select_callback = on_select
        self._column_names = list(self.COLUMNS.keys())
        super().__init__(parent, columns=self._column_names, show='headings', **kwargs)
        
        self.original_data = []
        self.current_data = []
        self.sort_column = None
        self.sort_reverse = False
        self._resize_timer = None
        
        self.translation_filter_var = tk.StringVar(value='全部')
        self.filter_texts = {col: '' for col in self._column_names}
        
        self._init_filters()
        self._init_columns()
        self.bind('<<TreeviewSelect>>', self._on_select)
        self.bind('<Control-a>', lambda e: self.selection_set(self.get_children()))
        self._bind_resize()

    def _bind_resize(self):
        """绑定父容器resize事件，实现列宽自适应"""
        self.master.bind('<Configure>', self._on_parent_resize)

    def _on_parent_resize(self, event):
        """父容器尺寸变化时自动调整列宽"""
        if event.widget != self.master:
            return
        
        if self._resize_timer:
            self.master.after_cancel(self._resize_timer)
        self._resize_timer = self.master.after(100, self._adjust_column_widths)

    def _adjust_column_widths(self):
        """根据父容器宽度，文件/原文/译文三列均分剩余宽度，索引列固定"""
        self.master.update_idletasks()
        parent_width = self.master.winfo_width()
        
        if parent_width < 100:
            return
            
        index_col = self.COLUMNS.get('index', {})
        fixed_width = index_col.get('width', 55)
        
        visible_stretchable = [
            key for key, config in self.COLUMNS.items() 
            if config.get('stretch') and self.column(key, 'width') > 0
        ]
        num_stretchable = len(visible_stretchable)
        
        available_width = max(0, parent_width - fixed_width - 80)
        col_width = int(available_width / num_stretchable) if num_stretchable > 0 else 200
        col_width = max(100, col_width)
        
        for key in visible_stretchable:
            self.column(key, width=col_width)

    def _init_columns(self):
        """根据COLUMNS配置初始化列"""
        for key, val in self.COLUMNS.items():
            self.heading(key, text=val.get('label', ''), command=lambda c=key: self.sort_by_column(c))
            width = val.get('width', 200)
            self.column(key, width=width, anchor=val.get('anchor', 'w'), stretch=val.get('stretch', True))
        
        self.after(100, self._adjust_column_widths)

    def _init_filters(self):
        """初始化筛选控件"""
        self.filter_frame = ttkb.Frame(self.master)
        self.filter_frame.pack(fill=tk.X, pady=(0, 5))
        self.filter_entries = {}

        for key, val in self.COLUMNS.items():
            if val.get('filter') == 'regex':
                frame = ttkb.Frame(self.filter_frame)
                frame.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
                ttkb.Label(frame, text=val.get('label')).pack(side=tk.LEFT)
                val = ttkb.Entry(frame, width=10)
                val.pack(side=tk.LEFT, fill=tk.X, expand=True)
                val.bind('<KeyRelease>', lambda e, c=key: self._on_filter_change(c))
                self.filter_entries[key] = val
            elif val.get('filter') == 'multiselect':
                frame_file = ttkb.Frame(self.filter_frame)
                frame_file.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
                ttkb.Label(frame_file, text=val.get('label')).pack(side=tk.LEFT)
                self.file_picker = MultiCombobox(master=frame_file, values=[], width=12)
                self.file_picker.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
                self.file_picker.bind("<<MultiSelectChanged>>", lambda e: self.apply_filters())

        ttkb.Label(self.filter_frame, text='匹配模式:').pack(side=tk.LEFT, padx=(10, 2))
        self.regex_options = MultiCombobox(
            self.filter_frame, width=15,
            values=['忽略大小写 (i)', '多行模式 (m)', '点匹配换行 (s)'])
        self.regex_options.pack(side=tk.LEFT, padx=2)
        self.regex_options.bind("<<MultiSelectChanged>>", lambda e: self.apply_filters())

        ttkb.Label(self.filter_frame, text='状态:').pack(side=tk.LEFT, padx=(10, 2))
        state_combo = ttkb.Combobox(
            self.filter_frame, textvariable=self.translation_filter_var,
            values=['全部', '已翻译', '未翻译'], state='readonly', width=8)
        state_combo.pack(side=tk.LEFT, padx=2)
        state_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())

        ttkb.Button(
            self.filter_frame, text='清除筛选',
            command=self.clear_filters).pack(side=tk.RIGHT, padx=5)

    def _on_select(self, event):
        """选中事件处理"""
        if self._on_select_callback:
            self._on_select_callback(self.get_selected_items_data())

    def _on_filter_change(self, col_name):
        """筛选条件变更处理"""
        if col_name in self.filter_entries:
            self.filter_texts[col_name] = self.filter_entries[col_name].get().strip()
        self.apply_filters()

    def get_regex_flags_list(self) -> List[str]:
        """获取正则表达式标志列表"""
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
        """设置正则表达式标志列表"""
        desc_map = {'i': '忽略大小写 (i)', 'm': '多行模式 (m)', 's': '点匹配换行 (s)'}
        values = [desc_map[f] for f in flag_list if f in desc_map]
        self.regex_options.set_selected(values)

    def set_view_mode(self, show_file_column: bool = True, show_translation_column: bool = True):
        """设置视图模式，控制列的显示隐藏"""
        if show_file_column:
            self.column('path', width=200, stretch=True)
        else:
            self.column('path', width=0, stretch=False)
            
        if show_translation_column:
            self.column('translation', width=200, stretch=True)
        else:
            self.column('translation', width=0, stretch=False)
            
        self.after(50, self._adjust_column_widths)

    def clear_filters(self):
        """清除所有筛选条件"""
        for key, val in self.filter_entries.items():
            if isinstance(val, ttkb.Entry):
                val.delete(0, tk.END)
                self.filter_texts[key] = ''
        self.file_picker.select_reset()
        self.translation_filter_var.set('全部')
        self.apply_filters()

    def apply_filters(self):
        """应用筛选条件"""
        if not self.original_data:
            self.current_data = []
            self.refresh_display()
            return

        selected_files = set(self.file_picker.get_selected())
        flags = self._compile_regex_flags()

        filtered_data = []
        for item in self.original_data:
            file_path = item.get('_file', '')
            if file_path and file_path not in selected_files:
                continue
            if not self._match_text_filters(item, flags):
                continue
            if not self._match_translation_status(item):
                continue

            filtered_data.append(item)

        self.current_data = filtered_data
        self.refresh_display()

    def _compile_regex_flags(self) -> int:
        """编译正则表达式标志"""
        flags = 0
        for flag_char in self.get_regex_flags_list():
            if flag_char == 'i':
                flags |= re.IGNORECASE
            elif flag_char == 'm':
                flags |= re.MULTILINE
            elif flag_char == 's':
                flags |= re.DOTALL
        return flags

    def _match_text_filters(self, item: Dict, flags: int) -> bool:
        """匹配文本筛选条件"""
        for key, val in self.COLUMNS.items():
            if val.get('filter') == 'regex':
                pattern = self.filter_texts.get(key, '')
                if pattern:
                    if not re.search(pattern, str(item.get(val.get('label'), '')), flags):
                        return False
        return True

    def _match_translation_status(self, item: Dict) -> bool:
        """匹配翻译状态筛选"""
        status = self.translation_filter_var.get()
        if status == '全部':
            return True
        
        trans = item.get('译文', '')
        orig = item.get('原文', '')
        
        if status == '已翻译':
            return bool(trans) and trans != orig
        elif status == '未翻译':
            return not trans or trans == orig
        return True

    def clear_items(self):
        """清空表格数据"""
        self.delete(*self.get_children())

    def _save_selection(self) -> List[Dict]:
        """保存当前选中状态"""
        return self.get_selected_items_data()

    def _restore_selection(self, saved_items: List[Dict]):
        """恢复选中状态"""
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

    @staticmethod
    def _get_offset_color(hex_color: str, offset=10):
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
        """刷新显示"""
        saved_items = self._save_selection()
        self.clear_items()
        for idx, item in enumerate(self.current_data):
            vals = [item.get(val['label'], '') for val in self.COLUMNS.values()]
            tag = 'oddrow' if idx % 2 == 0 else 'evenrow'
            self.insert('', 'end', values=vals, tags=(str(idx), tag))
        self._restore_selection(saved_items)

    def set_data(self, data: List[Dict]):
        """设置数据并刷新"""
        self.original_data = data.copy()
        self.current_data = data.copy()
        all_files = sorted({d['_file'] for d in data if d.get('_file')})
        self.file_picker.set_values(all_files)
        self.file_picker.select_reset()
        self.apply_filters()

    def set_filter_texts(self, filter_texts_dict: Dict[str, str]):
        """设置筛选文本"""
        for col_name, text in filter_texts_dict.items():
            if col_name in self.filter_entries:
                self.filter_texts[col_name] = text
                entry = self.filter_entries[col_name]
                if isinstance(entry, ttkb.Entry):
                    entry.delete(0, tk.END)
                    entry.insert(0, text)
        self.apply_filters()

    def get_filter_texts(self) -> Dict[str, str]:
        """获取筛选文本"""
        return {key: self.filter_texts.get(key, '')     
                for key, val in self.COLUMNS.items()
                    if val.get('filter') == 'regex'}

    def get_selected_items_data(self) -> List[Dict]:
        """获取选中项数据"""
        data = []
        for iid in self.selection():
            tags = self.item(iid, 'tags')
            if tags:
                idx = int(tags[0])
                if idx < len(self.current_data):
                    data.append(self.current_data[idx])
        return data

    def sort_by_column(self, col_name: str):
        """按列排序"""
        if not self.current_data:
            return
        
        col_config = self.COLUMNS.get(col_name)
        if not col_config:
            return
            
        self.sort_reverse = not self.sort_reverse if self.sort_column == col_name else False
        self.sort_column = col_name
        
        def sort_key(item):
            value = item.get(col_config['label'], '')
            if col_config['type'] == 'number':
                return int(value) if value else 0
            return str(value).lower()
            
        self.current_data.sort(key=sort_key, reverse=self.sort_reverse)
        self.refresh_display()

    def get_total_count(self) -> int:
        """获取当前显示数据总数"""
        return len(self.current_data)

    def clear_selection(self):
        """清除选中状态"""
        self.selection_remove(self.selection())
