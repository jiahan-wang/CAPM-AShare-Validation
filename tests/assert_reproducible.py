# -*- coding: utf-8 -*-
"""assert_reproducible.py — CI数值回归断言: 重算表 vs committed表 分系数容差比对
容差设计(评审P1: 分系数层级):
  β/R²/adjR² 绝对1e-6 | α 绝对1e-9 | SE 相对1e-6 | p值 相对1e-3或同显著桶
  JB统计量 相对1e-4 | n/lag_used/year 精确相等 | rolling逐点比对
用法: python src/py/assert_reproducible.py <committed_tables_dir>
退出码: 0=全部通过, 1=任一不一致
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np

committed = sys.argv[1]
local = 'results/tables'

KEYS = {
    'base_canonical.machine.csv': ['code'],
    'robust_hac.machine.csv': ['track', 'code'],
    'subsample_year.machine.csv': ['code', 'year'],
    'chow924.machine.csv': ['code'],
    'rf_appendix.machine.csv': ['code'],
    'extended_annual.machine.csv': ['code', 'year'],
    'extended_periods.machine.csv': ['code', 'period'],
    'rolling_beta.machine.csv': ['code', 'date'],
}
ABS_COLS = {'beta': 1e-6, 'r2': 1e-6, 'adj_r2': 1e-6, 'alpha': 1e-9,
            'alpha_excess': 1e-9, 'delta': 1e-12, 'beta_rf0': 1e-6, 'beta_rfconst': 1e-6,
            'se': 1e-8, 'lo': 1e-6, 'hi': 1e-6}
REL_PREFIX = {'se_': 1e-6, 'bw_raw': 1e-6}

fails = []
for fn, keys in KEYS.items():
    p_c, p_l = os.path.join(committed, fn), os.path.join(local, fn)
    if not (os.path.exists(p_c) and os.path.exists(p_l)):
        fails.append(f'{fn}: 文件缺失'); continue
    c = pd.read_csv(p_c, dtype={'code': str})
    l = pd.read_csv(p_l, dtype={'code': str})
    if len(c) != len(l):
        fails.append(f'{fn}: 行数 {len(c)} vs {len(l)}'); continue
    m = c.merge(l, on=keys, suffixes=('_c', '_l'))
    if len(m) != len(c):
        fails.append(f'{fn}: 键不匹配 {len(m)} vs {len(c)}'); continue
    for col in c.columns:
        if col in keys: continue
        if not pd.api.types.is_numeric_dtype(c[col]):
            if (m[f'{col}_c'].fillna('') != m[f'{col}_l'].fillna('')).any():
                fails.append(f'{fn}.{col}: 非数值列不一致')
            continue
        a = m[f'{col}_c'].astype(float).values; b = m[f'{col}_l'].astype(float).values
        both_nan = np.isnan(a) & np.isnan(b)
        if (np.isnan(a) != np.isnan(b)).any():
            fails.append(f'{fn}.{col}: NaN位置不一致'); continue
        a, b = a[~both_nan], b[~both_nan]
        if len(a) == 0: continue
        if col in ('n', 'lag_used', 'year'):
            bad = np.abs(a - b) > 0
        elif col in ABS_COLS:
            bad = np.abs(a - b) > ABS_COLS[col]
        elif col.startswith('se_'):
            bad = np.abs(a - b) > 1e-6 * np.maximum(np.abs(b), 1e-12)
        elif col.startswith('p_') or col == 'p':
            # 相对1e3或同显著桶(极小p下溢时相对差无意义)
            same_bucket = ((a < 1e-8) & (b < 1e-8)) | ((a < 0.01) & (b < 0.01)) | ((a < 0.05) & (b < 0.05)) | ((a >= 0.05) & (b >= 0.05))
            bad = ~(same_bucket | (np.abs(a - b) <= 1e-3 * np.maximum(np.abs(b), 1e-300)))
        elif col == 'jb_stat':
            bad = np.abs(a - b) > 1e-4 * np.maximum(np.abs(b), 1e-12)
        else:
            bad = np.abs(a - b) > 1e-6
        if bad.any():
            i = int(np.argmax(bad))
            fails.append(f'{fn}.{col}: {int(bad.sum())}处不一致, 例 a={a[i]:.10g} b={b[i]:.10g}')
    print(f'checked {fn}: {len(c)}行 × {len([x for x in c.columns if x not in keys])}列')

print()
if fails:
    print('断言失败:'); [print(' -', f) for f in fails]; sys.exit(1)
print('全部数值回归断言通过')
