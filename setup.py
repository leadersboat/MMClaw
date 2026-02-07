from setuptools import setup, find_packages

setup(
    name="pipclaw",  # PyPI 上的包名
    version="0.1.0",
    author="Your Name",
    description="🐈 PipClaw: Ultra-Lightweight, Pure Python Agent.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourname/pipclaw",
    
    # 自动寻找项目中的包目录 (即 pipclaw 文件夹)
    packages=find_packages(),
    
    # 这里是蹭热点的关键：让用户能直接运行命令
    entry_points={
        "console_scripts": [
            "pipclaw=pipclaw.main:main", # 格式: 命令名=包名.文件:函数名
        ],
    },
    
    # 既然是 Pure Python，尽量减少强制依赖
    install_requires=[
        "requests",
        "openai",
        "pyTelegramBotAPI",
    ],
    
    python_requires=">=3.8",
)