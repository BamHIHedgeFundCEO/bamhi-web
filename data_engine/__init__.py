"""
data_engine 動態路由器
自動尋找: data_engine / {category} / {module_name}.py
"""
import importlib

def get_data(category: str, module_name: str, ticker: str):
    if not module_name:
        return None
        
    try:
        # 動態載入模組，例如 data_engine.rates.treasury
        mod = importlib.import_module(f"data_engine.{category}.{module_name}")
        return mod.fetch_data(ticker)
    except Exception as e:
        print(f"⚠️ 無法載入 data_engine.{category}.{module_name}: {e}")
        return None