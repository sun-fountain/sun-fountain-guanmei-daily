# 官媒日报（个人版）

每天 07:00（北京时间）自动抓取人民日报、湖北日报要闻，十堰日报全文（剔除广告），竹山报全文（周刊，自动取最新一期），
用大模型精炼成一句话摘要，生成一个手机友好的 H5 页面部署到 GitHub Pages。

## 部署步骤（约 10 分钟，无需 git 命令）

1. **注册 GitHub 账号**：github.com，免费。
2. **建仓**：右上角 `+` → `New repository` → 名字填 `guanmei-daily` → 选 **Public** → 勾选 "Add a README" → Create。
   （Pages 免费托管要求 Public 仓库；私密性靠页面口令门保障。）
3. **上传代码**：解压本代码包 → 仓库页点 `Add file` → `Upload files` → 把**所有文件和文件夹**（含 `.github` 文件夹，上传网页上先点 "choose your files" 后选整个文件夹）拖进去 → Commit changes。
4. **设置大模型密钥**：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`
   - `LLM_API_KEY`：你的 Kimi（月之暗面）API key，platform.moonshot.cn 申请
   - `SITE_PASS`：你自定义的访问口令（例如 `woaimama2026`）
5. **（可选）换模型**：`Settings` → `Secrets and variables` → `Actions` → `Variables` 页签
   - `LLM_BASE_URL` = `https://api.moonshot.cn/v1`
   - `LLM_MODEL` = `moonshot-v1-8k`（或其他 OpenAI 兼容接口的 model 名）
6. **开 Pages**：`Settings` → `Pages` → Source 选 **Deploy from a branch** → Branch 选 `main`、目录选 `/site` → Save。
7. **手动跑一次测试**：`Actions` → 左侧 `daily` → 右侧 `Run workflow`。变绿后等 1 分钟，访问
   `https://你的用户名.github.io/guanmei-daily/` 输入口令即可看。

## 说明

- GitHub 定时任务（cron）可能有随机延迟，通常几分钟内。
- 湖北日报数字报上午才上线，07:00 若未更新会先显示最近一期，10:00 会自动补抓。
- 竹山报为周刊，无当日新期时自动展示最新一期。
- 首次运行后若某家报纸抓取为 0 篇（十堰日报数字报有反爬，最可能出问题），把 Actions 日志发我调整。
- 页面口令门是"防君子不防小人"级别，只用于避免公开访问，请勿存放任何隐私数据。
