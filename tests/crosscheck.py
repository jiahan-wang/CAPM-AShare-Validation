# -*- coding: utf-8 -*-
"""crosscheck.py — 跨语言平行复核: statsmodels重算R侧结果
复核对象: base_canonical(OLS β/α) 与 robust_hac(HC3/Newey-West SE)
容差: β/α 1e-10; SE 1e-8 (HAC核函数实现差异的合理量级)
运行: venv python tests/crosscheck.py  (离线, 只读committed CSV)
退出码: 0=全部通过, 1=有不一致(打印明细)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tests/ → 仓库根

import pandas as pd, numpy as np, statsmodels.api as sm

TOL_BETA, TOL_SE = 1e-10, 1e-8
fails = []

r = pd.read_csv('data/processed/returns_daily.csv').rename(columns=lambda c: str(c))
can = pd.read_csv('results/tables/base_canonical.machine.csv', dtype={'code': str}).set_index('code')
rob = pd.read_csv('results/tables/robust_hac.machine.csv', dtype={'code': str})
rd = rob[rob.track == 'daily'].set_index('code')
rw = rob[rob.track == 'weekly'].set_index('code')
retw = pd.read_csv('data/processed/returns_weekly.csv').rename(columns=lambda c: str(c))

def cmp(name, a, b, tol):
    ok = abs(a - b) < tol
    print(f"{'PASS' if ok else 'FAIL'}  {name}: py={a:.12g} R={b:.12g} |Δ|={abs(a-b):.2e}")
    if not ok: fails.append(name)

for code in can.index:
    y = r[code].values; x = sm.add_constant(r['CSI300'].values)
    ols = sm.OLS(y, x).fit()
    cmp(f'{code} beta(OLS)', ols.params[1], can.loc[code, 'beta'], TOL_BETA)
    cmp(f'{code} alpha(OLS)', ols.params[0], can.loc[code, 'alpha'], TOL_BETA)
    hc3 = sm.OLS(y, x).fit(cov_type='HC3')
    lag = int(rd.loc[code, 'lag_used'])
    hac = sm.OLS(y, x).fit(cov_type='hac', cov_kwds={'maxlags': lag})
    cmp(f'{code} se_hc3', hc3.bse[1], rd.loc[code, 'se_hc3'], TOL_SE)
    cmp(f'{code} se_nw', hac.bse[1], rd.loc[code, 'se_nw'], TOL_SE)

for code in rw.index:                       # 周频NW复核: y/x联合dropna, 防两列缺失位置不同导致错位
    d2 = retw[[code, 'CSI300']].dropna()
    y = d2[code].values
    x = sm.add_constant(d2['CSI300'].values)
    lag = int(rw.loc[code, 'lag_used'])
    hac = sm.OLS(y, x).fit(cov_type='hac', cov_kwds={'maxlags': lag})
    cmp(f'W {code} se_nw', hac.bse[1], rw.loc[code, 'se_nw'], TOL_SE)

# Newey-West(1994)经验带宽公式独立核验(不依赖bwNeweyWest): floor(4*(n/100)^(2/9))
nobs = len(r)
formula_cap = int(np.floor(4 * (nobs/100) ** (2/9)))
print(f"INFO  NW(1994)公式带宽上限 floor(4*({nobs}/100)^(2/9)) = {formula_cap}; "
      f"bwNeweyWest实测(日频) = {sorted(rd.lag_used.tolist())} (数据驱动, 允许超/低于上限)")

print(f"\n共{len(fails)}处失败" if fails else "\n全部复核通过")
sys.exit(1 if fails else 0)
