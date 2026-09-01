# 01_clean.R — 收益率矩阵构建（v3·第2步前置）
# 输入: data/raw/*.csv (date, close)   输出: data/processed/returns_daily.csv, returns_weekly.csv
# canonical口径: 以沪深300指数交易日历为主干reindex个股; 停牌日不前向填充(该日该股为NA,
#   回归时按完整观测对剔除); 对数收益 diff(log(P)); 周频=每周最后交易日, 周内日对数收益求和
# 运行方式: 仓库根目录下 Rscript src/R/01_clean.R
suppressPackageStartupMessages({library(readr)})

args <- commandArgs(FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) > 0) {
  script_path <- normalizePath(sub("^--file=", "", file_arg[1]))
  root <- normalizePath(file.path(dirname(script_path), "..", ".."))
  setwd(root)
}

D_RAW <- "data/raw"; D_PROC <- "data/processed"
dir.create(D_PROC, showWarnings = FALSE, recursive = TRUE)

codes <- c("600519","600036","300750","000333","600276","600900")

load_close <- function(f) {
  d <- read_csv(f, show_col_types = FALSE)
  data.frame(date = as.Date(d$date), close = as.numeric(d$close))
}

idx <- load_close(file.path(D_RAW, "index_000300.csv"))
prices <- data.frame(date = idx$date, CSI300 = idx$close)
for (code in codes) {
  d <- load_close(file.path(D_RAW, paste0(code, "_hfq.csv")))
  prices[[code]] <- d$close[match(prices$date, d$date)]   # 指数日历为主干
}
na_days <- colSums(is.na(prices[, -1, drop = FALSE]))
message("缺失日统计(含warm-up): ", paste(names(na_days), na_days, sep = "=", collapse = " "))

# 全窗口(含2023-12-29 warm-up)逐列对齐差分, 再截取收益样本期
ret <- prices
for (cc in names(prices)[-1]) {
  x <- as.numeric(prices[[cc]])
  r <- rep(NA_real_, nrow(prices))
  ok <- !is.na(x)
  idx <- which(ok)
  r[idx[-1]] <- diff(log(x[idx]))          # 差分对齐到后一行, 严防错位
  gaps <- which(ok[-1] & !ok[-length(ok)]) # 停牌后首个交易日
  r[gaps + 1] <- NA_real_                  # 跨停牌收益置NA, 不前向填充
  ret[[cc]] <- r
}
ret <- ret[prices$date >= "2024-01-01" & prices$date <= "2025-12-31", ]
rownames(ret) <- NULL
write.csv(ret, file.path(D_PROC, "returns_daily.csv"), row.names = FALSE)
message("日收益矩阵: n=", nrow(ret), " (验收预期≈484)")

# 周频: ISO周键, 取每周最后交易日为标签, 周内日对数收益求和(等价 ln(P末/P上周末))
ret$week <- format(ret$date, "%G-W%V")
stopifnot(!any(is.na(ret$CSI300)))          # 指数主干不应有缺失
weekly <- do.call(rbind, lapply(split(ret, ret$week), function(g) {
  g <- g[!is.na(g$week), , drop = FALSE]
  vals <- lapply(codes, function(cc) if (all(!is.na(g[[cc]]))) sum(g[[cc]]) else NA_real_)
  out <- data.frame(date = max(g$date), CSI300 = sum(g$CSI300))
  for (i in seq_along(codes)) out[[codes[i]]] <- vals[[i]]
  out
}))
rownames(weekly) <- NULL
weekly <- weekly[order(weekly$date), ]
write.csv(weekly, file.path(D_PROC, "returns_weekly.csv"), row.names = FALSE)
message("周收益矩阵: n=", nrow(weekly), " (两年≈100-103周, 验收预期≈100±4)")
