import os
import subprocess

def compile_resources():
    """将资源文件编译成Python模块"""
    try:
        # 尝试使用pyrcc6（如果PyQt6-tools已安装）
        subprocess.run(['pyrcc6', 'resources.qrc', '-o', 'resources_rc.py'], check=True)
        print("资源文件编译成功，使用pyrcc6")
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            # 尝试使用pyside6-rcc（如果PySide6已安装）
            subprocess.run(['pyside6-rcc', 'resources.qrc', '-o', 'resources_rc.py'], check=True)
            print("资源文件编译成功，使用pyside6-rcc")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("错误: 无法编译资源文件。请确保已安装PyQt6-tools或PySide6")
            return False
    return True

if __name__ == "__main__":
    compile_resources() 