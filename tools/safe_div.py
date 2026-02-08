"""
安全除法
"""
import numpy as np

def safe_div(a, b, default=0):
     return np.divide(a, b, out=np.full_like(a, default, dtype=np.float64), where=b != 0)
