"""
市場部門經理
"""
from . import breadth
from . import strength  # 👈 新增這行

def update():
    print("🔹 [Market Dept] 開始更新...")
    breadth.update()
    strength.update()   # 👈 新增這行