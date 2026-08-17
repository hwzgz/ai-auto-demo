import os
import subprocess
import zipfile
from dotenv import load_dotenv
import requests

load_dotenv()

# =========配置区 Agnes API =========
SOURCE_FILE = "main.py"
ZIP_OUTPUT = "fixed_project.zip"
MAX_RETRY = 8
API_KEY = os.getenv("AGNES_API_KEY")
API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
MODEL_NAME = "agnes-2.5-pro-alpha"
# ===================================

def run_code(file_path: str) -> tuple[int, str, str]:
    """运行指定py文件，返回返回码、stdout、stderr"""
    proc = subprocess.Popen(
        ["python", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr

def get_fixed_code(source_code: str, error_msg: str) -> str:
    prompt = f"""
你是Python代码调试专家。
原始代码：
```python
{source_code}