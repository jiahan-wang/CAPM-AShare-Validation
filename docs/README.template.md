# CAPM模型在A股市场的适用性：六大行业龙头的实证检验与稳健性分析

![CI](https://github.com/jiahan-wang/CAPM-AShare-Validation/actions/workflows/ci.yml/badge.svg)

## English Summary

Single-factor CAPM tests on six A-share industry leaders (Kweichow Moutai, China Merchants Bank, CATL, Midea, Hengrui, Yangtze Power) against the CSI 300 index, 2024–2025 daily data (~{{N_DAILY}} observations per stock).

**Pipeline**: Sina hfq prices → log returns → OLS market regressions → HC3 & Newey-West robust inference (data-driven bandwidths, recorded per stock and frequency) → 120-day rolling betas with 95% bands → yearly subsamples + event-window sensitivity → 10-year (2015–2025) extended robustness appendix.

**Engineering**: every number in this README is auto-generated from committed CSV fixtures (SHA-256 manifest in `data/meta/`); CI reruns the full R pipeline on every push and asserts machine-precision agreement; all estimates independently reproduced in Python/statsmodels (agreement <1e-14).

**Headline**: betas range from {{B_MAX}} (CATL, aggressive) to {{B_MIN}} (Yangtze Power, near-decoupled from the market); five of six alphas are indistinguishable from zero under all standard-error variants; Moutai's negative alpha is the exception — significant under all variants at weekly frequency (p≈{{MT_A_W_RANGE}}) and under HAC at daily frequency (p≈{{MT_A_NW_D}}), a criterion sensitivity we report rather than resolve; residuals are strongly leptokurtic (Jarque–Bera p < 0.001 for all six).

---

## 核心结论

CAPM对A股龙头**方向上成立、程度上分化**：六只β在OLS与NW下全部显著为正（HC3下长江电力p≈{{CHANGDIAN_HC3_P}}，见稳健推断表），但大盘对长江电力的解释力只有{{R2_MIN}}——单因子模型覆盖不了所有商业模式；α五只无法拒绝为0，茅台是唯一例外：周频三种标准误下均显著为负（p≈{{MT_A_W_RANGE}}），日频仅HAC显著（p≈{{MT_A_NW_D}}），两种结果并列展示；β本身随时间明显漂移，静态点估计必须配稳健推断和稳定性检验才可信。

## 研究问题

1. CAPM能否解释A股龙头企业的收益变动？（β显著性、R²解释力度）
2. 模型适用性在不同行业间是否存在系统性差异？
3. 龙头股是否存在可稳定获取的超额收益α？β在时间上稳定吗？

## 数据与口径

| 项目 | 设定 |
|---|---|
| 个股 | 贵州茅台600519 / 招商银行600036 / 宁德时代300750 / 美的集团000333 / 恒瑞医药600276 / 长江电力600900 |
| 市场基准 | 沪深300指数（价格指数） |
| 价格基准 | **后复权（hfq）**，主源新浪（见设计决策1、2） |
| 收益率 | 日对数收益 rₜ=ln(Pₜ/Pₜ₋₁)；周频=周内日收益之和 |
| 样本区间 | 2024-01-02 ~ 2025-12-31，日频n={{N_DAILY}}，周频n={{N_WEEKLY}} |
| 对齐方式 | 以指数交易日历为主干按日期键对齐；停牌不前向填充（本样本无停牌缺失） |
| 无风险利率 | 主回归取Rf≈0（日度约0.0055% vs 个股日波动>0.8%；常数Rf下β不受影响，仅α平移，附录实测Δβ<1e-12，机器精度量级，属浮点尾数噪声） |
| 极端值 | 涨跌停日保留，肥尾交由稳健推断处理 |
| 数据来源 | AkShare接口抓取，抓取日期与SHA-256清单见`data/meta/`，数据已随仓库提交、无需联网即可复现分析 |

## 方法

单因子时间序列回归：Rᵢ,ₜ = αᵢ + βᵢ·Rₘ,ₜ + εᵢ

**适用性判据**（研究约定，非学界统一标准；结论以连续量呈现为主，二分标签仅作概括）：β显著为正、R²度量解释力度、α是否可拒绝为0。

**推断**：同时报告OLS经典、HC3、Newey-West（Bartlett核，带宽由`bwNeweyWest()`按数据实测：{{BW_LIST_D}}；周频另行实测，互不复用）三套标准误。

## 核心结果

### 主回归（日频，2024-2025，经典OLS）

{{TBL_CANONICAL}}

### 稳健推断（日频，β标准误与p值三套对照）

{{TBL_ROBUST}}

> 波动聚集与异方差是真实存在的：稳健SE为OLS的{{SE_RATIO_RANGE}}倍、多数在1.4倍以上（statsmodels跨语言复核确认非实现误差）。长江电力在HC3下β的p值≈{{CHANGDIAN_HC3_P}}，属边缘显著，两种推断结果均列入下方α表。

{{TBL_ALPHA}}

### 周频对照（非同步交易的稳健性检验：R²升降双向都可能出现）

{{TBL_WEEKLY}}

### β随时间漂移：滚动窗口与分年

![rolling beta](results/figures/rolling_beta_panel.png)

{{TBL_SUBSAMPLE}}

924行情（2024-09-24政策组合拳）前后交互项F检验：六只p值均>0.05（长江电力p={{CHOW_MIN_P}}接近阈值，该结论对其偏脆弱），本样本内不构成结构断点；窗口较短，仅作敏感性检验。

### 十年扩展稳健性（2015-2025，同源数据）

![annual beta](results/figures/beta_annual_panel.png)

{{TBL_PERIODS}}

十年视角的关键事实：长江电力{{YANGDI_LOWBETA}}，说明"类债化"是结构特征而非本样本期的偶然；茅台、美的、招行的β在2024-2025明显走低，说明"龙头β"本身是时变的，任何静态点估计都应配稳定性检验。

## 设计决策与踩过的坑

1. **数据源事故**：最初用东方财富`stock_zh_a_hist`的hfq数据，三源交叉验证（东财×新浪×腾讯）发现其**非除权日的日收益也被系统性压缩**（例：2024-09-24招行真实涨幅+5.40%（新浪、腾讯一致），东财hfq算出+3.95%；485天中471天|Δr|>1bp），不满足"复权因子在事件间恒定"的基本性质。全部主源切换为新浪`stock_zh_a_daily(hfq)`并重建结果。上述对照可用`evidence/incident_check.py`联网复跑核验（输出`evidence/incident_check.csv`），事件记录存档于`data/meta/fetch_metadata.json`。原计划的yfinance镜像因Yahoo持续限流（HTTP 429）未建成；个股层面的全量第三方校验未做，仅完成招行样本的三源对照，已记为待办。
2. **选hfq不选qfq**：后复权以上市日为锚，历史窗口内价格不随未来分红修订，fixture更稳定。
3. **对数收益**：时间可加（周收益=日收益求和）；代价是组合加总需用简单收益（列入局限）。
4. **Rf≈0**：日频无风险利率与股票波动差两个数量级，常数Rf只平移α不改β（附录实测机器精度级不变）；时变Rf序列因接口不可用未做，已记录。
5. **停牌处理**：日历主干+不前向填充——填零收益会伪造低波动、污染NW带宽估计。
6. **跨语言复核**：R的β/α/HC3/NW全部用statsmodels重算，30项断言最大偏差为机器精度级（<1e-14）（`tests/crosscheck.py`）。
7. **差分错位bug**：R逻辑索引赋值`r[ok] <- diff(x[ok])`会让整列收益错位一天（diff少一行触发recycling），修复为按位置索引赋值，并用三个手工抽查点验证。

## 已知局限

- 样本为6只行业龙头（选题设计如此），不覆盖中小盘；结论不外推至全市场
- 单因子设定，未纳入规模/价值/盈利等Fama-French因子——对美的、长电这类CAPM解释力偏弱的样本，多因子可能显著提升解释力，留作后续
- 主窗口仅两年，时期偏差以2015-2025扩展附录部分缓解，仍非全周期检验
- 日频单因子回归受非同步交易影响（可能抬高R²），以周频对照部分回应，未做Dimson修正
- 多重检验未做形式校正：按单股（6股各3种SE）阈值0.05/6≈0.0083，六只β均显著；按全部36次检验的严格阈值0.05/36≈0.0014，长江电力（NW p={{CHANGDIAN_NW_P}}）不再显著，其余五只不受影响
- 沪深300全收益指数（H00300）敏感性因数据接口不可用未做，价格指数口径对α的影响留待补验

## 复现

```bash
# 分析（离线, 数据已提交, 无需下载）
Rscript -e "renv::restore()"   # 首次运行: 按renv.lock装齐R依赖
Rscript src/R/01_clean.R      # 收益率矩阵
Rscript src/R/02_base.R       # 主回归 + JB + 诊断图
Rscript src/R/03_robust.R     # HC3/Newey-West + rf附录
Rscript src/R/04_rolling.R    # 滚动β + 分年子样本 + 924敏感性
Rscript src/R/05_extended.R   # 十年扩展稳健性

# 跨语言复核（可选, 需Python; 建议干净venv, 版本与CI一致; 其他较新版本通常亦可）
python -m venv .venv && pip install -r requirements.txt
python tests/crosscheck.py   # 30项断言, 退出码0=通过

# 数据刷新（联网, 手动; 会更新fixture与SHA-256清单）
python src/py/fetch_data.py
```

环境：R 4.4.1（`renv.lock`锁包版本）；Python ≥3.11（`requirements.txt`）。README中全部数字由`src/py/gen_readme.py`从`results/tables/`自动生成，与仓库内表格逐位一致。

复现范围：分析链字节级可复现；`fetch_data.py`为一次性存档流程（元数据含手工标注字段，见`data/meta/fetch_metadata.json`的`manual_annotations`）；数据源事故对照经`evidence/incident_check.py`联网复跑核验。

## 目录结构

```
├── data/raw/          六股+指数 日收盘价CSV（fixture, SHA-256见meta）
├── data/raw_ext/      2015-2025十年OHLC（扩展附录用）
├── data/processed/    日/周收益率矩阵
├── data/meta/         抓取元数据 + SHA-256清单 + 数据源事故记录
├── evidence/          数据源事故的联网复跑核验脚本与输出
├── src/py/            取数 / README生成脚本
├── tests/             跨语言复核 + 数值回归断言
├── docs/              README模板
├── src/R/             01~05 分析流水线
├── results/tables/    全部机器精度结果表（README数字来源）
└── results/figures/   诊断图 / 滚动β面板 / 年度β面板
```

## 数据声明

行情数据经AkShare抓取（新浪/腾讯/东财公开接口），版权归原数据源所有，本仓库仅存档研究复现所需的最小价格序列。

## License

MIT — Jiahan Wang, 2026
