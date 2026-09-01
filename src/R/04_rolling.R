# 04_rolling.R — 滚动β(120日窗口+95%置信带) + 自然年子样本 + 924交互项检验
# 运行: 仓库根目录 Rscript src/R/04_rolling.R
# 规则: 滚动窗内用解析SE(小窗稳健SE噪声大); NA异常=窗口起点后连续>20(119个结构性NA属正常起点);
#       924只作敏感性(交互项F检验), 不写结论; 置信带用 β ± 1.96*SE
suppressPackageStartupMessages({library(readr)})

args <- commandArgs(FALSE)
fa <- grep("^--file=", args, value = TRUE)
if (length(fa) > 0) setwd(normalizePath(file.path(dirname(sub("^--file=", "", fa[1])), "..", "..")))

codes <- c("600519","600036","300750","000333","600276","600900")
en <- c("600519"="Moutai","600036"="CMB","300750"="CATL","000333"="Midea","600276"="Hengrui","600900"="YangtzePower")
WIN <- 120; STEP <- 1

ret <- read_csv("data/processed/returns_daily.csv", show_col_types = FALSE)
ret$date <- as.Date(ret$date)
n_all <- nrow(ret)

# ---------- 滚动β ----------
roll <- list()
for (code in codes) {
  y <- ret[[code]]; x <- ret$CSI300
  pts <- list(); i <- 1
  while (i + WIN - 1 <= n_all) {
    j <- i + WIN - 1
    yy <- y[i:j]; xx <- x[i:j]
    if (all(!is.na(yy))) {
      m <- lm(yy ~ xx); s <- summary(m)
      pts[[length(pts)+1]] <- data.frame(code=code, date=ret$date[j],
        beta=unname(coef(m)[2]), se=unname(s$coefficients[2,2]),
        lo=unname(coef(m)[2]-1.96*s$coefficients[2,2]),
        hi=unname(coef(m)[2]+1.96*s$coefficients[2,2]))
    } else {
      pts[[length(pts)+1]] <- data.frame(code=code, date=ret$date[j], beta=NA, se=NA, lo=NA, hi=NA)
    }
    i <- i + STEP
  }
  roll[[code]] <- do.call(rbind, pts)
}
rolling <- do.call(rbind, roll); rownames(rolling) <- NULL
write.csv(rolling, "results/tables/rolling_beta.machine.csv", row.names = FALSE)
cat("滚动β点数/股:", nrow(rolling)/6, "(预期", floor((n_all-WIN)/STEP)+1, ")\n")
# NA异常检查: 结构性前119点之外, 连续>20个NA才报警
for (code in codes) {
  g <- rolling[rolling$code==code, ]
  tail_na <- rle(is.na(g$beta))
  bad <- any(tail_na$values & tail_na$lengths > 20)
  if (bad) cat("NA异常:", code, "\n")
}
cat("NA检查完成(无输出=全部正常)\n")

png("results/figures/rolling_beta_panel.png", width=2000, height=1400, res=150)
par(mfrow=c(2,3), mar=c(3.5,4,2.5,1))
for (code in codes) {
  g <- rolling[rolling$code==code, ]
  full_beta <- unname(coef(lm(ret[[code]] ~ ret$CSI300))[2])
  plot(g$date, g$beta, type="l", lwd=1.6, col="steelblue",
       xlab="", ylab="beta (120d)", main=en[code])
  polygon(c(g$date, rev(g$date)), c(g$lo, rev(g$hi)),
          col=adjustcolor("steelblue", alpha.f=0.18), border=NA)
  abline(h=full_beta, lty=2, col="darkred"); abline(h=1, lty=3, col="gray60")
}
dev.off()
cat("图: results/figures/rolling_beta_panel.png\n")

# ---------- 自然年子样本 ----------
sub <- list()
for (code in codes) {
  for (yr in c(2024, 2025)) {
    g <- ret[format(ret$date, "%Y")==yr, ]
    m <- lm(g[[code]] ~ g$CSI300); s <- summary(m)
    sub[[paste(code,yr)]] <- data.frame(code=code, year=yr, n=nobs(m),
      beta=unname(coef(m)[2]), se=unname(s$coefficients[2,2]), p=unname(s$coefficients[2,4]),
      r2=s$r.squared)
  }
}
subsample <- do.call(rbind, sub); rownames(subsample) <- NULL
write.csv(subsample, "results/tables/subsample_year.machine.csv", row.names = FALSE)
cat("\n子样本表: results/tables/subsample_year.machine.csv\n")
print(subsample, digits=4)

# ---------- 924交互项检验(敏感性) ----------
ret$post <- as.integer(ret$date >= as.Date("2024-09-24"))
inter <- list()
for (code in codes) {
  dd <- data.frame(y = ret[[code]], x = ret$CSI300, post = ret$post)
  dd <- dd[complete.cases(dd), ]
  m0 <- lm(y ~ x, data = dd)
  m1 <- lm(y ~ x * post, data = dd)
  at <- anova(m0, m1)
  inter[[code]] <- data.frame(code=code, F=at$F[2], p=at$`Pr(>F)`[2])
}
itab <- do.call(rbind, inter); rownames(itab) <- NULL
write.csv(itab, "results/tables/chow924.machine.csv", row.names = FALSE)
cat("\n924交互项F检验(敏感性): \n"); print(itab, digits=4)
