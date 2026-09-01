# 05_extended.R — 十年扩展稳健性附录(2015-2025, 新浪hfq, 与主分析同源)
# 运行: 仓库根目录 Rscript src/R/05_extended.R
# 输入: data/raw_ext/{code}_hfq_ohlc.csv + data/raw_ext/index_000300_ohlc_full.csv
# 输出: results/tables/extended_annual.machine.csv, extended_periods.machine.csv
#       results/figures/beta_annual_panel.png
# 内置校验: 2024/2025分年结果必须与subsample_year.machine.csv一致(<1e-10), 否则stop
suppressPackageStartupMessages({library(readr)})

args <- commandArgs(FALSE)
fa <- grep("^--file=", args, value = TRUE)
if (length(fa) > 0) setwd(normalizePath(file.path(dirname(sub("^--file=", "", fa[1])), "..", "..")))

codes <- c("600519","600036","300750","000333","600276","600900")
en <- c("600519"="Moutai","600036"="CMB","300750"="CATL","000333"="Midea","600276"="Hengrui","600900"="YangtzePower")

idx <- read_csv("data/raw_ext/index_000300_ohlc_full.csv", show_col_types = FALSE)
idx$date <- as.Date(idx$date)
rx <- c(NA, diff(log(idx$close)))
R <- data.frame(date = idx$date, CSI300 = rx)
for (code in codes) {
  d <- read_csv(sprintf("data/raw_ext/%s_hfq_ohlc.csv", code), show_col_types = FALSE)
  d$date <- as.Date(d$date)
  r <- rep(NA_real_, nrow(R))
  pos <- match(d$date, R$date)
  rr <- c(NA, diff(log(d$close)))
  r[pos[-1]] <- rr[-1]                     # 按日期落位
  R[[code]] <- r
}
R <- R[R$date >= "2015-01-01" & R$date <= "2025-12-31", ]

fit1 <- function(y, x) {
  ok <- complete.cases(y, x)
  if (sum(ok) < 30) return(NULL)
  m <- lm(y[ok] ~ x[ok]); s <- summary(m)
  data.frame(n = sum(ok), beta = unname(coef(m)[2]), se = unname(s$coefficients[2,2]),
             p = unname(s$coefficients[2,4]), r2 = s$r.squared)
}

# ---------- 分年β ----------
ann <- list()
for (yr in 2015:2025) for (code in codes) {
  g <- R[format(R$date, "%Y") == yr, ]
  f <- fit1(g[[code]], g$CSI300)
  if (!is.null(f)) ann[[paste(code, yr)]] <- data.frame(code = code, year = yr, f)
}
annual <- do.call(rbind, ann); rownames(annual) <- NULL
write.csv(annual, "results/tables/extended_annual.machine.csv", row.names = FALSE)

# ---------- 内置校验: 与主分析分年表一致 ----------
sub <- read_csv("results/tables/subsample_year.machine.csv", show_col_types = FALSE)
sub$year <- as.integer(sub$year); annual$year <- as.integer(annual$year)
mg <- merge(annual, sub, by = c("code","year"), suffixes = c(".ext",".main"))
stopifnot(nrow(mg) == 12)
dmax <- max(abs(mg$beta.ext - mg$beta.main))
cat("校验 分年β(2024/2025) 扩展表vs主表 最大偏差 =", format(dmax, digits=3), "\n")
if (dmax > 1e-10) stop("扩展表与主表分年结果不一致 — 存在bug")
cat("校验通过\n")

# ---------- 分时期β ----------
periods <- list("2015-2017" = c("2015-01-01","2017-12-31"),
                "2018-2020" = c("2018-01-01","2020-12-31"),
                "2021-2023" = c("2021-01-01","2023-12-31"),
                "2024-2025" = c("2024-01-01","2025-12-31"))
per <- list()
for (nm in names(periods)) for (code in codes) {
  g <- R[R$date >= as.Date(periods[[nm]][1]) & R$date <= as.Date(periods[[nm]][2]), ]
  f <- fit1(g[[code]], g$CSI300)
  if (!is.null(f)) per[[paste(code, nm)]] <- data.frame(code = code, period = nm, f)
}
periods_tab <- do.call(rbind, per); rownames(periods_tab) <- NULL
write.csv(periods_tab, "results/tables/extended_periods.machine.csv", row.names = FALSE)

# ---------- 年度β面板图 ----------
png("results/figures/beta_annual_panel.png", width = 1600, height = 1000, res = 150)
par(mar = c(4, 4, 2, 1))
yrs <- sort(unique(annual$year))
mat <- sapply(codes, function(cc) {
  v <- rep(NA_real_, length(yrs))
  g <- annual[annual$code == cc, ]
  v[match(g$year, yrs)] <- g$beta; v
})
line_cols <- c("darkred","steelblue","darkgreen","orange3","purple3","gray40")
matplot(yrs, mat, type = "b", pch = 16, lwd = 1.8, lty = 1,
        col = line_cols,
        xlab = "year", ylab = "beta (annual OLS)", ylim = c(0, max(mat, na.rm = TRUE) * 1.1))
legend("topright", legend = en[codes], col = line_cols, pch = 16, lwd = 2, bty = "n", cex = 0.9)
abline(h = 1, lty = 3, col = "gray60")
dev.off()
cat("图: results/figures/beta_annual_panel.png\n")
cat("分年表行数:", nrow(annual), "| 分时期表行数:", nrow(periods_tab), "\n")
