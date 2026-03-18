import os
import subprocess
import sys


def build_with_nuitka():
    """使用 Nuitka 打包应用程序，并包含 QML 资源。"""

    if not os.path.exists("icon.ico"):
        print("错误：找不到 icon.ico 文件，请确保它存在于当前目录")
        return False

    if not os.path.isdir("qml"):
        print("错误：找不到 qml 目录，请确认界面资源完整")
        return False

    python_exe = sys.executable or "python"
    nuitka_cmd = [
        python_exe,
        "-m",
        "nuitka",
        "--onefile",
        "--standalone",
        "--windows-console-mode=disable",
        "--enable-plugin=pyqt6",
        "--include-qt-plugins=qml",
        "--include-data-files=icon.ico=icon.ico",
        "--include-data-dir=qml=qml",
        "--windows-icon-from-ico=icon.ico",
        "--output-dir=dist",
        "main.py",
    ]

    print(f"执行命令: {' '.join(nuitka_cmd)}")

    try:
        subprocess.run(nuitka_cmd, check=True)
        print("打包成功！输出目录: dist/")
        return True
    except subprocess.CalledProcessError as exc:
        print("打包失败: 请确认已安装 nuitka，可执行 `uv sync` 或 `uv pip install nuitka` 后重试。")
        print(exc)
        return False


if __name__ == "__main__":
    build_with_nuitka()
