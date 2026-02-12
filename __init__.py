"""
data_engine：依 category 分派請求，取得報價與歷史數據。
"""
from . import rates
from . import equity
from . import crypto


def get_data(category: str, ticker: str):
    """
    依分類分派到對應模組的 fetch_data(ticker)。
    回傳 {"value": float, "change_pct": float, "history": DataFrame} 或 None。
    """
    modules = {
        "rates": rates,
        "equity": equity,
        "crypto": crypto,
    }
    mod = modules.get(category)
    if mod is None:
        return None
    return mod.fetch_data(ticker)
