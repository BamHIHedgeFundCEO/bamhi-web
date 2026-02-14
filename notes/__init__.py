"""
notes 動態路由器
自動尋找: notes / {category} / {module_name}.py
"""
import importlib

def fetch_note(category: str, module_name: str, ticker: str):
    if not module_name:
        return "⚠️ 設定檔缺少 module 參數"
        
    try:
        # 動態載入模組，例如 notes.rates.treasury
        mod = importlib.import_module(f"notes.{category}.{module_name}")
        if hasattr(mod, "get_note"):
            return mod.get_note(ticker)
        else:
            return f"⚠️ {module_name}.py 裡面沒有定義 get_note(ticker) 函式"
    except Exception:
        return f"⚠️ 尚未建立 notes/{category}/{module_name}.py 筆記檔案"