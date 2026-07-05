import json
import os
import tkinter as tk
import tkinter.font as tkfont
import ttkbootstrap as ttkb
from typing import Optional, List, Dict, Any

from mcntools.config import FONT_DEFAULT, IMAGE_EXTS, JSON_EXT

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False





class JSONPreviewNode:
    __slots__ = ['key', 'value', 'path', 'start_line', 'end_line', 'folded', 'children']

    def __init__(self, key: str, value: Any, path: str, start_line: int, end_line: int):
        self.key = key
        self.value = value
        self.path = path
        self.start_line = start_line
        self.end_line = end_line
        self.folded = False
        self.children: List['JSONPreviewNode'] = []


class TextPreview(ttkb.Frame):
    """文本/JSON 预览：行号、JSON 高亮、JSON 折叠"""

    @staticmethod
    def _theme_colors():
        try:
            return ttkb.Style().colors
        except Exception:
            return None

    def __init__(self, master, font=FONT_DEFAULT, json_mode: bool = False, readonly: bool = False, **kw):
        super().__init__(master, **kw)
        self.font = font
        self._tkfont = tkfont.Font(self, font=self.font)
        self._json_mode = json_mode
        self._readonly = readonly
        self._root_node: Optional[JSONPreviewNode] = None
        self._node_by_line: Dict[int, JSONPreviewNode] = {}

        self.gutter = tk.Canvas(self, width=56, highlightthickness=0, borderwidth=0)
        self.text = tk.Text(self, font=self.font, wrap=tk.NONE, padx=4, undo=False,
                            spacing1=0, spacing3=0)
        self.yscroll = ttkb.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.xscroll = ttkb.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.config(yscrollcommand=self._on_yview, xscrollcommand=self.xscroll.set)

        self.gutter.grid(row=0, column=0, sticky='ns')
        self.text.grid(row=0, column=1, sticky='nsew')
        self.yscroll.grid(row=0, column=2, sticky='ns')
        self.xscroll.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._setup_tags()
        self._bind_events()
        self._setup_context_menu()
        self.apply_theme()

    def _setup_tags(self):
        self.text.tag_config('elide', elide=True)

    def _bind_events(self):
        self.text.bind('<Configure>', lambda e: self._redraw_gutter())
        self.text.bind('<KeyRelease>', lambda e: self._redraw_gutter())
        self.bind('<Configure>', lambda e: self._redraw_gutter())
        self.text.bind('<Button-3>', self._show_context_menu)

    def _setup_context_menu(self):
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="展开子项", command=self._expand_key_value)
        self._context_menu.add_command(label="折叠子项", command=self._collapse_key_value)
        self._context_menu.add_command(label="折叠其他", command=self._collapse_others_key_value)

    def _show_context_menu(self, event):
        self.current_line = self.text.index(f"@{event.x},{event.y}")
        if self._json_mode:
            if self._node_by_line:
                self._context_menu.post(event.x_root, event.y_root)

    def _get_current_line(self):
        idx = getattr(self, 'current_line', self.text.index(tk.CURRENT))
        return int(idx.split('.')[0])

    def _expand_key_value(self):
        line = self._get_current_line()
        node = self._find_key_node(line)
        if node and node.end_line > node.start_line:
            self._set_node_fold(node, False)
            self._refresh_folds()
            self._redraw_gutter()

    def _collapse_key_value(self):
        line = self._get_current_line()
        node = self._find_key_node(line)
        if node and node.end_line > node.start_line:
            self._set_node_fold(node, True)
            self._refresh_folds()
            self._redraw_gutter()

    def _collapse_others_key_value(self):
        line = self._get_current_line()
        node = self._find_key_node(line)
        if node:
            self._set_node_fold(self._root_node, True, lambda n: not node.path.startswith(n.path))
            self._refresh_folds()
            self._redraw_gutter()

    def _set_node_fold(self, node: JSONPreviewNode, folded: bool, filter=None):
        if not filter or filter(node):
            node.folded = folded
        for child in node.children:
            self._set_node_fold(child, folded, filter)

    def _find_key_node(self, line: int) -> Optional[JSONPreviewNode]:
        node = self._node_by_line.get(line)
        if node:
            return node
        for n in reversed(self._node_by_line.values()):
            if n.start_line <= line <= n.end_line:
                return n
        return None

    def apply_theme(self):
        c = self._theme_colors()
        if c:
            self.text.tag_config('json_key', foreground=c.fg)
            self.text.tag_config('json_string', foreground=c.danger)
            self.text.tag_config('json_number', foreground=c.success)
            self.text.tag_config('json_bool', foreground=c.info)
            self.text.tag_config('json_brace', foreground=c.secondary)
            self.gutter.config(bg=c.bg)
            self.gutter_fg = c.fg
            self.fold_color = c.fg
            self._redraw_gutter()

    def set_content(self, text: str):
        state = self.text.cget('state')
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', text)
        self.text.config(state=tk.DISABLED if self._readonly else state)
        self._root_node = None
        self._node_by_line = {}
        if self._json_mode:
            self._apply_json_highlight()
            self._build_json_cache(text)
            self._refresh_folds()
        self._redraw_gutter()

    def get_text(self) -> str:
        return self.text.get('1.0', tk.END + '-1c')

    def set_wrap(self, wrap: bool):
        self.text.config(wrap=tk.WORD if wrap else tk.NONE)
        self._redraw_gutter()

    def show_error(self, msg: str):
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', msg)
        self.text.config(state=tk.DISABLED)
        self._root_node = None
        self._node_by_line = {}
        self._redraw_gutter()

    def clear(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self._root_node = None
        self._node_by_line = {}
        self._redraw_gutter()

    def _apply_json_highlight(self):
        for tag in ('json_key', 'json_string', 'json_number', 'json_bool', 'json_brace'):
            self.text.tag_remove(tag, '1.0', tk.END)
        content = self.text.get('1.0', tk.END + '-1c')
        i = 0
        n = len(content)
        line = 1
        col = 0
        in_str = False
        escape = False
        tok_start = 0
        is_key = False
        while i < n:
            ch = content[i]
            if ch == '\n':
                line += 1
                col = 0
                i += 1
                continue
            if in_str:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_str = False
                    end_idx = f"{line}.{col + 1}"
                    tag = 'json_key' if is_key else 'json_string'
                    self.text.tag_add(tag, f"{line}.{tok_start}", end_idx)
                    is_key = False
            else:
                if ch == '"':
                    in_str = True
                    tok_start = col
                    j = i + 1
                    while j < n:
                        if content[j] == '"' and content[j - 1] != '\\':
                            break
                        j += 1
                    k = j + 1
                    while k < n and content[k] in ' \t\r\n':
                        k += 1
                    if k < n and content[k] == ':':
                        is_key = True
                elif ch.isdigit() or (ch == '-' and i + 1 < n and content[i + 1].isdigit()):
                    start_col = col
                    j = i
                    while j < n and content[j] in '-+eE0123456789.':
                        j += 1
                    self.text.tag_add('json_number', f"{line}.{start_col}", f"{line}.{start_col + (j - i)}")
                    col += (j - i)
                    i = j
                    continue
                elif content[i:i + 4] == 'true' or content[i:i + 5] == 'false':
                    word = 'true' if content[i:i + 4] == 'true' else 'false'
                    self.text.tag_add('json_bool', f"{line}.{col}", f"{line}.{col + len(word)}")
                    col += len(word)
                    i += len(word)
                    continue
                elif content[i:i + 4] == 'null':
                    self.text.tag_add('json_bool', f"{line}.{col}", f"{line}.{col + 4}")
                    col += 4
                    i += 4
                    continue
                elif ch in '{}[]':
                    self.text.tag_add('json_brace', f"{line}.{col}", f"{line}.{col + 1}")
            col += 1
            i += 1

    def _build_json_cache(self, text: str):
        try:
            data = json.loads(text)
        except Exception:
            return

        lines = text.split('\n')
        self._root_node = JSONPreviewNode('', data, '{0}', 1, len(lines))
        self._node_by_line[self._root_node.start_line] = self._root_node

        def find_value_lines(start_line: int, value: Any) -> tuple:
            line = start_line
            depth = 0
            in_str = False
            escape = False
            target_type = type(value).__name__
            
            full_text = '\n'.join(lines[start_line - 1:])
            for i, ch in enumerate(full_text):
                if ch == '\n':
                    line += 1
                    continue
                if in_str:
                    if escape:
                        escape = False
                    elif ch == '\\':
                        escape = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth += 1
                    if depth == 1:
                        target_type = 'dict'
                elif ch == '[':
                    depth += 1
                    if depth == 1:
                        target_type = 'list'
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and target_type == 'dict':
                        return (start_line, line)
                elif ch == ']':
                    depth -= 1
                    if depth == 0 and target_type == 'list':
                        return (start_line, line)
            return (start_line, len(lines))

        def parse_lines(data: Any, path: str, start_line: int, parent_node: JSONPreviewNode):
            current_line = start_line
            parent_node.path = path
            if isinstance(data, dict):
                for key, value in data.items():
                    key_line = current_line
                    while key_line <= len(lines):
                        line_content = lines[key_line - 1]
                        stripped = line_content.strip()
                        if stripped.startswith(f'"{key}":'):
                            break
                        key_line += 1
                    if key_line > len(lines):
                        continue
                    
                    value_start = key_line
                    line_content = lines[key_line - 1]
                    stripped = line_content.strip()
                    if ':' in stripped:
                        after_colon = stripped.split(':', 1)[1].strip()
                        if after_colon.startswith(('{', '[')):
                            value_start = key_line
                        else:
                            value_start = key_line + 1
                    
                    if isinstance(value, (dict, list)):
                        value_lines = find_value_lines(value_start, value)
                        node_path = f"{path}.{key}" if path else key
                        node = JSONPreviewNode(key, value, node_path, key_line, value_lines[1])
                        parent_node.children.append(node)
                        self._node_by_line[key_line] = node
                        parse_lines(value, node_path, value_start, node)
                        current_line = value_lines[1] + 1
                    else:
                        current_line = key_line + 1
            elif isinstance(data, list):
                for idx, value in enumerate(data):
                    idx_line = current_line
                    found = False
                    while idx_line <= len(lines):
                        line_content = lines[idx_line - 1]
                        stripped = line_content.strip()
                        if stripped.startswith(f'"{idx}"') or stripped == str(idx):
                            found = True
                            break
                        if isinstance(value, (dict, list)) and stripped.startswith(('{', '[')):
                            found = True
                            break
                        if stripped.startswith(('"', "'")) and not isinstance(value, (dict, list)):
                            found = True
                            break
                        if stripped.replace('-', '').isdigit() and isinstance(value, (int, float)):
                            found = True
                            break
                        idx_line += 1
                    if idx_line > len(lines) or not found:
                        continue
                    
                    value_start = idx_line
                    if isinstance(value, dict):
                        line_content = lines[idx_line - 1]
                        stripped = line_content.strip()
                        if stripped.startswith('{'):
                            value_start = idx_line
                        else:
                            value_start = idx_line + 1
                        
                        value_lines = find_value_lines(value_start, value)
                        node_path = f"{path}.{{{idx}}}" if path else f"{{{idx}}}"
                        node = JSONPreviewNode(str(idx), value, node_path, idx_line, value_lines[1])
                        parent_node.children.append(node)
                        self._node_by_line[idx_line] = node
                        parse_lines(value, node_path, value_start, node)
                        current_line = value_lines[1] + 1
                    elif isinstance(value, list):
                        line_content = lines[idx_line - 1]
                        stripped = line_content.strip()
                        if stripped.startswith('['):
                            value_start = idx_line
                        else:
                            value_start = idx_line + 1
                        
                        value_lines = find_value_lines(value_start, value)
                        node_path = f"{path}.[{idx}]" if path else f"[{idx}]"
                        node = JSONPreviewNode(str(idx), value, node_path, idx_line, value_lines[1])
                        parent_node.children.append(node)
                        self._node_by_line[idx_line] = node
                        parse_lines(value, node_path, value_start, node)
                        current_line = value_lines[1] + 1
                    else:
                        node_path = f"{path}.[{idx}]" if path else f"[{idx}]"
                        node = JSONPreviewNode(str(idx), value, node_path, idx_line, idx_line)
                        parent_node.children.append(node)
                        current_line = idx_line + 1

        parse_lines(data, self._root_node.path, self._root_node.start_line, self._root_node)

    def _refresh_folds(self):
        self.text.tag_remove('elide', '1.0', tk.END)

        def apply_folds(node: JSONPreviewNode):
            if node.folded:
                self.text.tag_add('elide', f"{node.start_line + 1}.0", f"{node.end_line}.0")
            for child in node.children:
                apply_folds(child)

        if self._root_node:
            apply_folds(self._root_node)

    def _toggle_fold(self, node: JSONPreviewNode):
        node.folded = not node.folded
        self._refresh_folds()
        self._redraw_gutter()

    def _on_yview(self, *args):
        self.yscroll.set(*args)
        self._redraw_gutter()

    def _redraw_gutter(self):
        self.gutter.delete('all')
        try:
            gw = self.gutter.winfo_width()
            txth = self.text.winfo_height()
        except Exception:
            return
        if gw < 5 or txth < 5:
            self.after(60, self._redraw_gutter)
            return
        last_line = int(self.text.index(tk.END + '-1c').split('.')[0])
        top_line = max(1, int(self.text.index('@0,0').split('.')[0]))
        li = top_line
        guard = 0
        while li <= last_line and guard < 5000:
            guard += 1
            try:
                bbox = self.text.bbox(f"{li}.0")
            except Exception:
                bbox = None
            if not bbox:
                li += 1
                continue
            _, y, _, h = bbox
            if y > txth:
                break
            cy = y + h // 2
            self.gutter.create_text(gw - 15, cy, text=str(li),
                                    anchor='e', font=self.font, fill=self.gutter_fg)
            node = self._node_by_line.get(li)
            if node and node.end_line > node.start_line:
                mid = self.gutter.create_text(
                    gw - 6, cy, text='❯', anchor='center', angle=0 if node.folded else -90,
                    font=('Segoe UI', 10), fill=self.fold_color, tags='foldmark')
                self.gutter.tag_bind(mid, '<Button-1>', lambda e, n=node: self._toggle_fold(n))
            li += 1


class ImagePreview(ttkb.Frame):
    """图片预览：自适应窗口 + 缩放"""

    @staticmethod
    def _theme_colors():
        try:
            return ttkb.Style().colors
        except Exception:
            return None

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._image = None
        self._photo = None
        self._scale = 1.0
        self._fit = True

        self.toolbar = ttkb.Frame(self)
        self.toolbar.pack(fill=tk.X, pady=(2, 2))
        ttkb.Button(self.toolbar, text="➕ 放大", command=lambda: self._zoom(1.25)).pack(side=tk.LEFT, padx=2)
        ttkb.Button(self.toolbar, text="➖ 缩小", command=lambda: self._zoom(1 / 1.25)).pack(side=tk.LEFT, padx=2)
        ttkb.Button(self.toolbar, text="📋 适应窗口", command=self._reset_fit).pack(side=tk.LEFT, padx=2)
        ttkb.Button(self.toolbar, text="🔄 实际大小", command=self._actual_size).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttkb.Label(self.toolbar, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=8)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Configure>', self._on_configure)
        self.canvas.bind('<MouseWheel>', self._on_wheel)
        self.apply_theme()

    def apply_theme(self):
        c = self._theme_colors()
        bg = c.bg if c is not None else '#ffffff'
        self.canvas.config(bg=bg)

    def set_content(self, content: bytes):
        if not PIL_AVAILABLE:
            self.canvas.delete('all')
            self.canvas.create_text(self.canvas.winfo_width() // 2 or 100,
                                    self.canvas.winfo_height() // 2 or 100,
                                    text="未安装 Pillow，无法预览图片",
                                    fill='red')
            return
        from io import BytesIO
        self._image = Image.open(BytesIO(content))
        self._image.load()
        self._fit = True
        self._render()

    def clear(self):
        self.canvas.delete('all')
        self._image = None
        self._photo = None

    def _on_configure(self, event):
        if self._fit:
            self._render()

    def _on_wheel(self, event):
        if not self._image:
            return
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self._zoom(factor)

    def _zoom(self, factor):
        if not self._image:
            return
        self._fit = False
        self._scale = max(0.05, min(self._scale * factor, 32.0))
        self._render()

    def _reset_fit(self):
        if not self._image:
            return
        self._fit = True
        self._render()

    def _actual_size(self):
        if not self._image:
            return
        self._fit = False
        self._scale = 1.0
        self._render()

    def _render(self):
        if not self._image:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            self.after(60, self._render)
            return
        iw, ih = self._image.size
        if self._fit:
            scale = min(cw / iw, ch / ih) if iw > 0 and ih > 0 else 1.0
            self._scale = scale
        scale = self._scale
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        try:
            resized = self._image.resize((nw, nh), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(resized)
        except Exception:
            return
        self.canvas.delete('all')
        self.canvas.create_image(cw // 2, ch // 2, image=self._photo, anchor='center')
        pct = int(self._scale * 100) if self._scale <= 32 else 3200
        self.zoom_label.config(text=f"{pct}%")


class FilePreview(ttkb.Frame):
    """统一文件预览：根据文件类型切换 文本/JSON/图片"""

    @staticmethod
    def _decode_text(content: bytes) -> Optional[str]:
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
        return None

    @staticmethod
    def _hex_dump(content: bytes, limit: int = 4096) -> str:
        text = "无法解码为文本，显示为二进制数据:\n\n"
        for i in range(0, min(len(content), limit), 16):
            chunk = content[i:i + 16]
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            text += f'{i:08x}: {hex_part:<48} {ascii_part}\n'
        if len(content) > limit:
            text += f'\n... (显示前{limit}字节，共{len(content)}字节)'
        return text

    @staticmethod
    def _looks_like_json(text: str) -> bool:
        s = text.lstrip()
        return s.startswith(('{', '[')) and s.rstrip().endswith(('}', ']'))

    def __init__(self, master, font=FONT_DEFAULT, **kw):
        super().__init__(master, **kw)
        self.font = font
        self._mode = None
        self._widget = None

    def set_content(self, path: str, content: bytes):
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTS and PIL_AVAILABLE:
            self._switch('image')
            self._widget.set_content(content)
            return

        text = self._decode_text(content)
        if text is not None:
            if ext == JSON_EXT or self._looks_like_json(text):
                self._switch('json')
                self._widget.set_content(self._pretty_json(text) if ext == JSON_EXT else text)
            else:
                self._switch('text')
                self._widget.set_content(text)
        else:
            self._switch('text')
            self._widget.set_content(self._hex_dump(content))

    @staticmethod
    def _pretty_json(text: str) -> str:
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=4)
        except Exception:
            return text

    def _switch(self, mode):
        if self._mode == mode and self._widget is not None:
            return
        if self._widget is not None:
            self._widget.destroy()
        if mode == 'image':
            self._widget = ImagePreview(self)
        else:
            self._widget = TextPreview(self, font=self.font,
                                       json_mode=(mode == 'json'),
                                       readonly=False)
        self._widget.pack(fill=tk.BOTH, expand=True)
        self._mode = mode

    def get_text(self) -> Optional[str]:
        if self._mode in ('text', 'json') and self._widget is not None:
            return self._widget.get_text()
        return None

    def set_wrap(self, wrap: bool):
        if self._mode in ('text', 'json') and self._widget is not None:
            self._widget.set_wrap(wrap)

    def show_error(self, msg: str):
        self._switch('text')
        self._widget.show_error(msg)

    def clear(self):
        if self._widget is not None:
            self._widget.clear()

    def apply_theme(self):
        if self._widget is not None and hasattr(self._widget, 'apply_theme'):
            self._widget.apply_theme()

    @property
    def mode(self):
        return self._mode