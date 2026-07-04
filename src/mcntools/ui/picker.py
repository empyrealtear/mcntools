import tkinter as tk
import ttkbootstrap as ttkb
from typing import List, Optional


class MultiSelectDropdown(ttkb.Frame):
    def __init__(self, master, values=(), width=12, max_visible=20, **kw):
        super().__init__(master, **kw)
        self._values = list(values)
        self._max_visible = max_visible
        self._selected: set = set()
        self._display_list: List[str] = []
        self._panel: Optional[ttkb.Frame] = None
        self._listbox: Optional[tk.Listbox] = None
        self._display_var = tk.StringVar(value='')

        self._entry = ttkb.Entry(self, textvariable=self._display_var, width=width, state="disabled")
        self._entry.pack(fill=tk.X)
        self._entry.bind('<Button-1>', lambda e: (self.toggle(), 'break'))
        self._entry.bind('<Key>', lambda e: (self.toggle(), 'break'))
        self.bind('<Destroy>', lambda e: self.hide(), add='+')

    def toggle(self):
        self.hide() if self._panel else self.show()

    def show(self):
        self.hide()
        top = self.winfo_toplevel()
        self._panel = ttkb.Frame(top, relief='solid', borderwidth=1, padding=2)

        bar = ttkb.Frame(self._panel)
        bar.pack(fill=tk.X, padx=4, pady=(4, 2))
        for txt, fn in [('全选', self.select_all), ('反选', self.invert)]:
            lb = ttkb.Label(bar, text=txt, cursor='hand2', style='PickerLink.TLabel')
            lb.pack(side=tk.LEFT, padx=(0, 12))
            lb.bind('<Button-1>', lambda e, f=fn: f())

        sv = tk.StringVar()
        entry = ttkb.Entry(bar, textvariable=sv, width=8)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        entry.bind('<KeyRelease>', lambda e: self._filter(sv.get()))

        lf = ttkb.Frame(self._panel)
        lf.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))

        self._listbox = tk.Listbox(lf, selectmode=tk.MULTIPLE,
                                   height=min(len(self._values), self._max_visible),
                                   exportselection=False,
                                   highlightthickness=0,
                                   borderwidth=0)
        self._listbox.grid(row=0, column=0, sticky='nsew')
        self._listbox.bind('<ButtonRelease-1>', self._on_click)

        self._vsb = ttkb.Scrollbar(lf, orient='vertical', command=self._listbox.yview)
        self._hsb = ttkb.Scrollbar(lf, orient='horizontal', command=self._listbox.xview)
        self._vsb.grid(row=0, column=1, sticky='ns')
        self._hsb.grid(row=1, column=0, sticky='ew')
        self._vsb.grid_remove()
        self._hsb.grid_remove()
        self._listbox.config(yscrollcommand=self._vsb.set, xscrollcommand=self._hsb.set)

        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        self._display_list = self._values.copy()
        self._fill()
        entry.focus_set()

        self.update_idletasks()
        x = self._entry.winfo_rootx() - top.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() - top.winfo_rooty()
        self._panel.place(x=x, y=y, width=max(self._entry.winfo_width(), 160))
        self._panel.update_idletasks()
        self._update_scrollbars()
        top.bind_all('<Button-1>', self._on_global, add='+')

    def _update_scrollbars(self):
        self._vsb.grid_remove()
        self._hsb.grid_remove()
        try:
            yv = self._listbox.yview()
            xv = self._listbox.xview()
            if yv[0] != 0.0 or yv[1] != 1.0:
                self._vsb.grid(row=0, column=1, sticky='ns')
            if xv[0] != 0.0 or xv[1] != 1.0:
                self._hsb.grid(row=1, column=0, sticky='ew')
        except tk.TclError:
            pass

    def _fill(self):
        if not self._listbox:
            return
        self._listbox.delete(0, tk.END)
        for v in self._display_list:
            mark = '▣ ' if v in self._selected else '▢ '
            self._listbox.insert(tk.END, mark + v)
        self._listbox.config(height=max(min(len(self._display_list), self._max_visible), 1))

    def _filter(self, kw):
        if not self._listbox:
            return
        kw = kw.strip()
        if not kw:
            self._display_list = self._values.copy()
        else:
            kwl = kw.lower()
            self._display_list = [v for v in self._values if kwl in v.lower()]
        removed = self._selected - set(self._display_list)
        if removed:
            self._selected -= removed
            self._refresh()
            self.event_generate('<<MultiSelectChanged>>')
        self._fill()
        self._update_scrollbars()

    def _on_click(self, event):
        if not self._listbox:
            return
        idx = self._listbox.nearest(event.y)
        if idx < 0 or idx >= len(self._display_list):
            return
        v = self._display_list[idx]
        if v in self._selected:
            self._selected.remove(v)
        else:
            self._selected.add(v)
        self._fill()
        self._refresh()
        self.event_generate('<<MultiSelectChanged>>')

    def _on_global(self, event):
        if not self._panel or not self._panel.winfo_exists():
            return
        w = event.widget
        try:
            if w != self._entry and not str(w).startswith(str(self._panel)):
                self.hide()
        except tk.TclError:
            pass

    def hide(self):
        if self._panel:
            try:
                self.winfo_toplevel().unbind_all('<Button-1>')
            except tk.TclError:
                pass
            try:
                self._panel.destroy()
            except tk.TclError:
                pass
            self._panel = None
            self._listbox = None
            self._vsb = None
            self._hsb = None

    def _refresh(self):
        n, total = len(self._selected), len(self._values)
        self._display_var.set('全部' if n == 0 or n == total else
                             next(iter(self._selected)) if n == 1 else
                             f'已选 {n} 项')

    def get_selected(self) -> List[str]:
        return [v for v in self._values if v in self._selected]

    def set_values(self, values):
        self.hide()
        self._values = list(values)
        self._selected &= set(self._values)
        self._refresh()

    def set_selected(self, selected: List[str]):
        self._selected = {v for v in selected if v in self._values}
        self._refresh()
        if self._listbox:
            self._fill()
        self.event_generate('<<MultiSelectChanged>>')

    def clear(self):
        self._selected.clear()
        self._refresh()
        if self._listbox:
            self._fill()
        self.event_generate('<<MultiSelectChanged>>')

    def select_all(self):
        self._selected |= set(self._display_list) if self._display_list else set(self._values)
        self._refresh()
        if self._listbox:
            self._fill()
        self.event_generate('<<MultiSelectChanged>>')

    def invert(self):
        for v in self._display_list:
            if v in self._selected:
                self._selected.remove(v)
            else:
                self._selected.add(v)
        self._refresh()
        if self._listbox:
            self._fill()
        self.event_generate('<<MultiSelectChanged>>')
