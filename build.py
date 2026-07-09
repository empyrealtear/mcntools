import subprocess
import sys
import os
import shutil


def get_version():
    version = "unknown"
    init_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "mcntools", "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    version = line.split("=")[1].strip().strip('"').strip("'")
                    break
    return version


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    version = get_version()
    app_name = f"mcntools_v{version}.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name={app_name}",
        "--icon=icon.ico",
        "--paths=src",
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

    print(f"开始打包 v{version}...")
    print("命令:", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if result.returncode == 0:
        print("\n打包成功!")
        print(f"输出文件: dist/{app_name}.exe")
        cleanup_files(app_name)
    else:
        print("\n打包失败!")
        print("标准输出:", result.stdout)
        print("错误信息:", result.stderr)


def cleanup_files(app_name="mcntools"):
    print("\n清理中间文件...")

    items_to_delete = [
        "build",
        f"{app_name}.spec",
        f"{app_name}.exe.manifest",
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