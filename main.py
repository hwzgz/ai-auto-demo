import os
import json
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Any

# Windows编码修复
if os.name == "nt":
    os.environ["PYTHONIOENCODING"] = "utf-8"

load_dotenv()

# ==========临时调试硬编码！上传GitHub务必删除这一行！==========
api_key = "sk-jY1RHERCuHkALKRzvcIvZHHmlOl0YuEUU1w3Z40loERoXMud"

client = OpenAI(
    api_key=api_key,
    base_url="https://apihub.agnes-ai.cn/v1"
)
MODEL = "agnes-2.5-flash"

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "数学计算器，执行加减乘除等数学运算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expr": {"type": "string", "description": "数学表达式，例如 128 * 56"}
                },
                "required": ["expr"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把文本内容写入本地磁盘文件，覆盖原有内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "文件名，例如 output.txt"},
                    "content": {"type": "string", "description": "要写入的文本内容"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取本地txt、md文本文件。**一旦成功拿到文件内容，绝对不要再重复调用read_file，不要尝试读取不存在的猜测文件名！**",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "明确存在的文件名，例如 plan.txt"}
                },
                "required": ["filename"]
            }
        }
    }
]

def call_tool(name: str, args: dict) -> str:
    try:
        if name == "calculator":
            expr = args["expr"]
            result = eval(expr)
            return f"计算成功，结果：{result}"
        elif name == "write_file":
            filename = args["filename"]
            content = args["content"]
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            return f"文件写入成功：{filename}"
        elif name == "read_file":
            filename = args["filename"]
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read()
            return f"读取文件 {filename} 成功，内容：\n{text}"
        else:
            return f"未知工具:{name}"
    except Exception as e:
        return f"工具执行异常：{str(e)}"

# ===================== SQLite数据库 =====================
DB_PATH = os.path.join("data", "ruflo.db")

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        main_task TEXT,
        sub_tasks TEXT,
        final_output TEXT,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

def save_task_record(main_task: str, sub_tasks: List[str], final_output: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sub_str = json.dumps(sub_tasks, ensure_ascii=False)
    cur.execute(
        "INSERT INTO tasks(main_task, sub_tasks, final_output) VALUES (?, ?, ?)",
        (main_task, sub_str, final_output)
    )
    conn.commit()
    conn.close()

init_db()

# ===================== Worker =====================
def run_worker(sub_task: str) -> str:
    sys_prompt = """你是子任务Worker。可用工具：calculator、write_file、read_file。
规则：
1. 只读取明确存在的文件，不要猜文件名。
2. 文件内容一旦获取，禁止再次调用read_file。
3. 拿到内容直接处理，不要反复读文件。"""
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"执行子任务：{sub_task}"}
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = resp.choices[0].message
    if msg.tool_calls:
        for tc in msg.tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)
            tool_result = call_tool(func_name, func_args)
            print(f"\n🔧 [Worker]调用工具 {func_name} 参数:{func_args}")
            print(f"🔧 [Worker]工具返回：{tool_result}")
            messages.append(msg)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})
        final_resp = client.chat.completions.create(model=MODEL, messages=messages)
        return final_resp.choices[0].message.content or ""
    return msg.content or ""

# ===================== Gather =====================
def run_gather(main_task: str, worker_results: List[Dict[str, str]]) -> str:
    prompt = f"""原始总任务：{main_task}
各个worker子任务执行结果：
{json.dumps(worker_results, ensure_ascii=False, indent=2)}

汇总全部输出，生成最终结果。已经拿到文件内容就不要再调用read_file。"""
    sys_prompt = "Gather汇总Agent，整合worker结果，禁止无意义重复读取文件。"
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt}
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = resp.choices[0].message
    if msg.tool_calls:
        for tc in msg.tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)
            tool_result = call_tool(func_name, func_args)
            print(f"\n🔧 [Gather]调用工具 {func_name} 参数:{func_args}")
            print(f"🔧 [Gather]工具返回：{tool_result}")
            messages.append(msg)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})
        final_resp = client.chat.completions.create(model=MODEL, messages=messages)
        return final_resp.choices[0].message.content or ""
    return msg.content or ""

# ===================== Queen调度器 =====================
class SwarmQueen:
    def split_task(self, main_task: str) -> List[str]:
        prompt = f"""把总任务拆分成独立子任务，只输出JSON数组，不要其他文字。
总任务：{main_task}
示例输出：["子任务1","子任务2"]"""
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":prompt}]
        )
        raw = resp.choices[0].message.content
        arr = json.loads(raw)
        return arr

    def run_swarm(self, main_task: str) -> Dict[str, Any]:
        print(f"\n👑 Queen收到总任务：{main_task}")
        sub_tasks = self.split_task(main_task)
        print(f"👑 拆分子任务列表：{sub_tasks}")
        worker_outputs = []
        for idx, st in enumerate(sub_tasks):
            print(f"\n🤖 Worker-{idx+1}开始执行：{st}")
            res = run_worker(st)
            worker_outputs.append({"sub_task": st, "result": res})
        final_result = run_gather(main_task, worker_outputs)
        print("\n👑 ===全部任务执行完毕===")
        save_task_record(main_task, sub_tasks, final_result)
        return {
            "main_task": main_task,
            "sub_tasks": sub_tasks,
            "worker_outputs": worker_outputs,
            "final_result": final_result
        }

# ===================== 入口 =====================
if __name__ == "__main__":
    queen = SwarmQueen()
    user_task = "读取plan.txt的内容，把这份每日计划修改成周末休闲版本，保存为weekend_plan.txt"

    try:
        out = queen.run_swarm(user_task)
        print("\n======== 📃最终结果 ========")
        print(out["final_result"])
    except Exception as err:
        print(f"\n❌程序发生错误：{err}")