# Security Policy

## 支持的版本 / Supported Versions

本项目是求职/研究用的数据分析作品集，不以生产系统形式维护安全更新。

| Version | Supported |
|---------|-----------|
| main（最新） | ✅ |

## 漏洞报告 / Reporting a Vulnerability

- **Python依赖**：如发现 `requirements*.txt` 中依赖存在安全公告（CVE / GHSA / PYSEC），请通过 GitHub Issues 报告，会尽快更新版本。
- **R依赖**：R包版本由 `renv.lock` 精确锁定；如发现其中某包存在安全公告，请在 Issues 注明包名与版本。
- **数据**：本仓库仅含公开行情价格的最小存档CSV（来源与抓取记录见 `data/meta/fetch_metadata.json`），不含任何个人信息或交易明细，无数据泄露面。

## 安全注意事项

- 分析全程离线：CI与本地复现均只读取已提交的数据fixture，不访问任何外部数据接口；取数脚本 `src/py/fetch_data.py` 为独立手动流程。
- 数据fixture以二进制方式入库并附SHA-256清单（`data/meta/sha256_manifest.json`），篡改或损坏可被逐文件校验发现。
- 本项目不包含模型文件加载逻辑（回归结果以CSV表格形式提交），不存在模型反序列化类攻击面。
