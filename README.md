\# Multi‑Agent本地文件读写Demo

基于OpenAI兼容接口的多Agent调度程序，支持读取、写入本地文本文件，数学计算，SQLite持久化任务记录。



\## 功能

\- 👑 Queen：大任务自动拆分为多个子任务

\- 🤖 Worker：独立执行子任务，调用工具

\- 📄 read\_file：读取本地txt/md文本文件

\- 💾 write\_file：生成并保存文本到本地文件

\- 🧮 calculator：数学表达式计算

\- 🗄️ SQLite：自动记录每次任务，存储在 data/



\## 安装依赖

```bash

pip install openai python-dotenv

