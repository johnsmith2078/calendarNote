import os
import subprocess
import sys

def build_with_nuitka():
    """使用Nuitka打包应用程序，确保包含图标文件"""
    
    # 检查icon.ico是否存在
    if not os.path.exists('icon.ico'):
        print("错误：找不到icon.ico文件，请确保它存在于当前目录")
        return False
    
    # Nuitka打包命令
    nuitka_cmd = [
        "python", "-m", "nuitka",
        "--onefile",
        "--standalone",                 # 创建独立的可执行文件
        "--windows-console-mode=disable",    # 禁用控制台窗口
        "--enable-plugin=pyqt6",        # 启用PyQt6插件
        "--include-data-files=icon.ico=icon.ico",  # 包含图标文件
        "--windows-icon-from-ico=icon.ico",       # 设置应用程序图标
        "--output-dir=dist",           # 输出目录
        "main.py"                      # 主脚本
    ]
    
    print(f"执行命令: {' '.join(nuitka_cmd)}")
    
    try:
        # 执行Nuitka打包命令
        subprocess.run(nuitka_cmd, check=True)
        print("打包成功！输出目录: dist/")
        return True
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

if __name__ == "__main__":
    build_with_nuitka() 