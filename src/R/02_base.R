# 02_base.R — base_canonical(主回归) + JB + 诊断图
# 运行: 仓库根目录 Rscript src/R/02_base.R
# 口径: 新浪hfq个股 × 沪深300指数, 指数日历主干对齐, 日对数收益, lm(ret ~ mkt)
suppressPackageStartupMessages({library(readr); library(tseries)})

args <- commandArgs(FALSE)
fa <- grep("^--file=", args, value = TRUE)
if (length(fa) > 0) setwd(normalizePath(file.path(dirname(sub("^--file=", "", fa[1])), "..", "..")))
dir.create("results/tables", showWarnings = FALSE, recursive = TRUE)
dir.create("results/figures", showWarnings = FALSE, recursive = TRUE)

codes <- c("600519","600036","300750","000333","600276","600900")
en_names <- c("600519"="Moutai","600036"="CMB","300750"="CATL",
              "000333"="Midea","600276"="Hengrui","600900"="YangtzePower")

fit_one <- function(y, x) {
  ok <- complete.cases(y, x); y <- y[ok]; x <- x[ok]
  m <- lm(y ~ x)
  s <- summary(m)
  data.frame(n = nobs(m),
             alpha = unname(coef(m)[1]), se_alpha = unname(s$coefficients[1,2]),
             t_alpha = unname(s$coefficients[1,3]), p_alpha = unname(s$coefficients[1,4]),
             beta = unname(coef(m)[2]), se_beta = unname(s$coefficients[2,2]),
             t_beta = unname(s$coefficients[2,3]), p_beta = unname(s$coefficients[2,4]),
             r2 = s$r.squared, adj_r2 = s$adj.r.squared,
             jb_stat = suppressWarnings(jarque.bera.test(residuals(m)))$statistic,
             jb_p = suppressWarnings(jarque.bera.test(residuals(m)))$p.value)
}

ret <- read_csv("data/processed/returns_daily.csv", show_col_types = FALSE)
ret$date <- as.Date(ret$date)
can_rows <- list()
for (code in codes) {
  m <- fit_one(ret[[code]], ret$CSI300)
  m$code <- code; m$track <- "canonical"
  can_rows[[code]] <- m
}
canonical <- do.call(rbind, can_rows)
write.csv(canonical, "results/tables/base_canonical.machine.csv", row.names = FALSE)

# ---------- sanity check: 排序符合经济直觉(高β进攻型在前, 类债公用事业垫底) ----------
chain <- function(v) names(sort(v, decreasing = TRUE))
cat("\n== canonical 排序链检查 ==\n")
beta_chain <- chain(setNames(canonical$beta, canonical$code))
r2_chain <- chain(setNames(canonical$r2, canonical$code))
exp_beta <- c("300750","600276","600519","600036","000333","600900")
exp_r2 <- c("300750","600519","600276","600036","000333","600900")
cat("β链:", paste(beta_chain, collapse = ">"), "| 预期: 300750>600276>600519>600036>000333>600900\n")
cat("R²链:", paste(r2_chain, collapse = ">"), "| 预期: 300750>600519>600276>600036>000333>600900\n")
cat("β链通过:", identical(beta_chain, exp_beta), "| R²链通过:", identical(r2_chain, exp_r2), "\n")

# ---------- 诊断图(英文标签, CI安全) ----------
for (code in codes) {
  ok <- complete.cases(ret[[code]], ret$CSI300)
  m <- lm(ret[[code]][ok] ~ ret$CSI300[ok])
  nm <- en_names[code]
  png(sprintf("results/figures/resid_%s.png", code), width = 1200, height = 1000, res = 150)
  par(mfrow = c(1, 2))
  plot(fitted(m), residuals(m), main = paste(nm, "- Residual vs Fitted"),
       xlab = "Fitted", ylab = "Residual"); abline(h = 0, lty = 2)
  qqnorm(residuals(m), main = paste(nm, "- Normal Q-Q")); qqline(residuals(m))
  dev.off()
}
cat("\n诊断图已输出 results/figures/resid_*.png (6张)\n")
