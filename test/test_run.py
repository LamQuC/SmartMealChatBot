import sys
from pathlib import Path

print("Python exec:", sys.executable)
print("CWD:", Path.cwd())

try:
    import langgraph
    from langgraph.graph import StateGraph, END
    from importlib.metadata import version
    lg_version = version("langgraph")
    print("langgraph OK:", lg_version)
except ModuleNotFoundError as e:
    raise RuntimeError(
        "Package langgraph chưa cài trong interpreter hiện tại. "
        "Chạy lại bằng .venv\\Scripts\\python.exe hoặc pip install langgraph"
    ) from e

from src.graph.worker import GraphWorker

worker = GraphWorker()

# Giả lập User lần đầu chưa có budget
print("--- Lần 1: Chưa có budget ---")
res1 = worker.run(user_id="lam_01", user_input="Tôi muốn lên thực đơn cho 4 người")
print("Chatbot:", res1.get("final_response"))

# Giả lập User trả lời budget
print("\n--- Lần 2: User cung cấp budget ---")
res2 = worker.run(user_id="lam_01", user_input="Khoảng 500k nhé")
print("Chatbot:", res2.get("final_response"))