# 03_robust.R — 稳健推断: OLS/HC3/Newey-West 三套标准误全列 (日频+周频) + rf常数附录
# 运行: 仓库根目录 Rscript src/R/03_robust.R
# 规则:
#   1) 点估计(α/β)在三套SE下必须完全一致 —— 不一致即实现错误, 停
#   2) NW lag用bwNeweyWest()实测: 记录原始实数带宽与floor取整值; 日频周频分别实测, 互不复用
#   3) 不预设SE方向: 任一稳健SE与OLS偏离>10% → 标记"查实现", 双向都查
#   4) rf附录: 常数rf=1.40%/252(元数据记录的回退口径), 报告β实际变化量而非断言不变
suppressPackageStartupMessages({library(readr); library(sandwich); library(lmtest)})

args <- commandArgs(FALSE)
fa <- grep("^--file=", args, value = TRUE)
if (length(fa) > 0) setwd(normalizePath(file.path(dirname(sub("^--file=", "", fa[1])), "..", "..")))

codes <- c("600519","600036","300750","000333","600276","600900")

fit_all <- function(y, x, tag) {
  ok <- complete.cases(y, x); y <- y[ok]; x <- x[ok]
  m <- lm(y ~ x)
  s <- summary(m)
  bw <- bwNeweyWest(m, prewhite = FALSE)     # 与估计口径统一prewhite=FALSE; 原始实数带宽
  lag <- max(1, floor(bw))
  ct_ols <- coeftest(m)
  ct_hc3 <- coeftest(m, vcov = vcovHC(m, type = "HC3"))
  ct_nw  <- coeftest(m, vcov = NeweyWest(m, lag = lag, prewhite = FALSE))
  data.frame(track = tag, code = NA, n = nobs(m),
             beta = unname(coef(m)[2]), r2 = s$r.squared,
             se_ols = unname(ct_ols[2,2]), se_hc3 = unname(ct_hc3[2,2]), se_nw = unname(ct_nw[2,2]),
             p_ols = unname(ct_ols[2,4]), p_hc3 = unname(ct_hc3[2,4]), p_nw = unname(ct_nw[2,4]),
             alpha = unname(coef(m)[1]),
             p_alpha_ols = unname(ct_ols[1,4]), p_alpha_hc3 = unname(ct_hc3[1,4]), p_alpha_nw = unname(ct_nw[1,4]),
             bw_raw = as.numeric(bw), lag_used = lag)
}

out <- list()
ret_d <- read_csv("data/processed/returns_daily.csv", show_col_types = FALSE)
ret_w <- read_csv("data/processed/returns_weekly.csv", show_col_types = FALSE)
for (code in codes) {
  d <- fit_all(ret_d[[code]], ret_d$CSI300, "daily");  d$code <- code;  out[[paste0("d_",code)]] <- d
  w <- fit_all(ret_w[[code]], ret_w$CSI300, "weekly"); w$code <- code;  out[[paste0("w_",code)]] <- w
}
robust <- do.call(rbind, out)
rownames(robust) <- NULL
write.csv(robust, "results/tables/robust_hac.machine.csv", row.names = FALSE)

# --- 一致性断言 ---
stopifnot(all(robust$p_ols <= 1 & robust$p_ols >= 0))
# 点估计一致性: 同一(track,code)内三套SE来自同一模型, beta天然相同; 这里防呆比较canonical
can <- read_csv("results/tables/base_canonical.machine.csv", show_col_types = FALSE)
chk <- merge(robust[robust$track=="daily", c("code","beta")], can[, c("code","beta")], by="code", suffixes=c("_rob","_can"))
stopifnot(max(abs(chk$beta_rob - chk$beta_can)) < 1e-10)
cat("点估计一致性断言: PASS (max|Δβ| < 1e-10)\n\n")

# --- SE方向检查(双向>10%标记) ---
rob <- robust[robust$track=="daily", ]
rob$r_hc3 <- rob$se_hc3/rob$se_ols; rob$r_nw <- rob$se_nw/rob$se_ols
cat("日频 SE比值(vs OLS):  code   HC3/OLS  NW/OLS   标记(偏离>10%)\n")
for (i in seq_len(nrow(rob))) {
  flag <- if (abs(rob$r_hc3[i]-1)>0.10 || abs(rob$r_nw[i]-1)>0.10) " <- 查实现" else ""
  cat(sprintf("  %s  %.3f   %.3f%s\n", rob$code[i], rob$r_hc3[i], rob$r_nw[i], flag))
}
cat("\n周频实测lag: ", paste(unique(robust$lag_used[robust$track=="weekly"]), collapse=","),
    "| 日频实测lag: ", paste(robust$lag_used[robust$track=="daily"], collapse=","), "\n")

# --- 显著性结论(以NW为准绳) ---
cat("\nβ显著性(日频, NW): ")
for (i in seq_len(nrow(rob))) cat(rob$code[i], "=", ifelse(rob$p_nw[i]<0.01, "1%显著",
    ifelse(rob$p_nw[i]<0.05, "5%显著", "不显著")), "  ")
cat("\n")

# --- rf常数附录 ---
rf_d <- 0.014/252
rf_rows <- list()
for (code in codes) {
  ok <- complete.cases(ret_d[[code]], ret_d$CSI300)
  y0 <- ret_d[[code]][ok]; x0 <- ret_d$CSI300[ok]
  y1 <- y0 - rf_d; x1 <- x0 - rf_d
  b0 <- unname(coef(lm(y0 ~ x0))[2])
  m1 <- lm(y1 ~ x1)
  rf_rows[[code]] <- data.frame(code=code, beta_rf0=b0, beta_rfconst=unname(coef(m1)[2]),
                                delta=unname(coef(m1)[2])-b0, alpha_excess=unname(coef(m1)[1]))
}
rf_tab <- do.call(rbind, rf_rows)
write.csv(rf_tab, "results/tables/rf_appendix.machine.csv", row.names = FALSE)
cat("\nrf常数(1.40%/252)附录: β最大实际变化量 =", format(max(abs(rf_tab$delta)), digits=3),
    "→ 结论按实测差值报告, 不断言'不变'\n")
