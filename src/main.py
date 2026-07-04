import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ttkbootstrap as ttkb

from mcntools.ui import JARClassTranslator


def main():
    root = ttkb.Window()
    app = JARClassTranslator(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()