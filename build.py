import subprocess
import sys
import os
import shutil


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=mcntools",
        "--icon=icon.ico",
        "--paths=src",
        "--hidden-import=mcntools",
        "--hidden-import=mcntools.config",
        "--hidden-import=mcntools.models",
        "--hidden-import=mcntools.models.data",
        "--hidden-import=mcntools.core",
        "--hidden-import=mcntools.core.translation_service",
        "--hidden-import=mcntools.core.jar_handler",
        "--hidden-import=mcntools.core.class_processor",
        "--hidden-import=mcntools.core.translation_manager",
        "--hidden-import=mcntools.core.backup_manager",
        "--hidden-import=mcntools.translators",
        "--hidden-import=mcntools.translators.base",
        "--hidden-import=mcntools.translators.google",
        "--hidden-import=mcntools.translators.deepseek",
        "--hidden-import=mcntools.translators.factory",
        "--hidden-import=mcntools.ui",
        "--hidden-import=mcntools.ui.main_window",
        "--hidden-import=mcntools.ui.workspace_tree",
        "--hidden-import=mcntools.ui.treeview",
        "--hidden-import=mcntools.ui.picker",
        "--hidden-import=mcntools.ui.preview",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=sklearn",
        "--exclude-module=torch",
        "--exclude-module=tensorflow",
        "--exclude-module=pyqt5",
        "--exclude-module=pyside6",
        "--exclude-module=wx",
        "--exclude-module=tkinter.test",
        "--exclude-module=tkinter.ttk.test",
        "--exclude-module=unittest",
        "--exclude-module=test",
        "--exclude-module=tests",
        "--exclude-module=setuptools",
        "--exclude-module=pip",
        "--exclude-module=distutils",
        "-y",
        "src/main.py",
    ]

    print("开始打包...")
    print("命令:", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if result.returncode == 0:
        print("\n打包成功!")
        print("输出文件: dist/mcntools.exe")

        cleanup_files()
    else:
        print("\n打包失败!")
        print("错误信息:", result.stderr)


def cleanup_files():
    print("\n清理中间文件...")

    items_to_delete = [
        "build",
        "mcntools.spec",
        "mcntools.exe.manifest",
    ]

    root_dir = os.path.dirname(os.path.abspath(__file__))

    for item in items_to_delete:
        path = os.path.join(root_dir, item)
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"  删除目录: {item}")
                else:
                    os.remove(path)
                    print(f"  删除文件: {item}")
            except Exception as e:
                print(f"  删除失败 {item}: {e}")

    print("清理完成!")


if __name__ == "__main__":
    main()
