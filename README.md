# **Glin**
*Your worklog, without the work.*

---

### ✨ What is Glin?
**Glin** is an [MCP server](https://modelcontextprotocol.io/) that **automatically builds your worklog** from two places you already live in:

- The **prompts and conversations** you have with your **agentic coding assistant**
- Your **git history**

No more manual logging. No more "what did I even do today?" moments.  
Glin captures your flow of work as it happens — transparently, in the background — and turns it into a clean, searchable record.

---

### 🔮 Why Glin?
Developers spend hours *doing*, but often forget the **telling**:
- Daily standups
- Sprint updates
- Performance reviews
- Knowledge transfer

Glin flips the script: your tools already know what you did — it just makes that knowledge **visible**.

Think of it as a **black box recorder for your dev work**: light, ambient, and surprisingly insightful.

---

### ⚡ Key Features
- **Transparent logging**: Captures coding activity without interrupting your flow
- **Git + AI context**: Merges commit history with assistant interactions
- **Human-friendly summaries**: Turn messy traces into readable narratives
- **MCP-native**: Integrates with any client that speaks MCP
- **Privacy-first**: You control what gets logged, stored, or shared



---

### 🧪 Running tests
This project uses pytest with coverage configured in pyproject.toml. You can run the test suite either directly or via the provided Makefile target.

Prerequisites:
- Python 3.13+
- One of:
  - uv (recommended)
  - or a Python virtual environment with pytest installed

Using uv (recommended):
1) Install dev dependencies:
   uv sync --group dev
2) Run tests:
   make test
   # or directly
   uv run pytest

Using pip/venv:
1) Create and activate a virtual environment, then install deps:
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   pip install pytest pytest-cov
2) Run tests:
   make test
   # or directly
   pytest

Notes:
- Coverage is enabled by default via pyproject addopts and will print a summary to the terminal and write coverage.xml in the repo root.
- Tests live under the tests/ directory and follow the patterns test_*.py or *_test.py.
