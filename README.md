# 晚安词卡

一个持续更新的考研英语阅读词卡静态站点，手机和电脑使用同一网址。首批为 **2010 年英语一 Text 4 的 32 张词卡**，默认 10 张轻复习。保留原有词汇、真题语境、词表释义和出处编号；没有上传完整 PDF 或原书。

> 交付状态：这是可部署的源代码，不代表 Pages 已经上线。首次仓库写入被平台安全检查拦截，远端发布尚未完成。

## 首次发布

把本项目文件放到 `qscefnthm/word_card` 的 main 分支根目录，再进入：

https://github.com/qscefnthm/word_card/settings/pages

在 **Build and deployment** 下选择 **Deploy from a branch → main → / (root) → Save**。

启用并成功完成首次部署后，默认地址应为 **https://qscefnthm.github.io/word_card/**，以 Pages 设置页实际状态为准。此后修改 main 的站点文件即可重新发布，不需要每天另建网站。

本项目不用 npm、不需要 API Key，也不需要配置 GitHub Actions 密钥。`.nojekyll` 必须一起上传；遗漏时也不应把 PDF 或其他无关文件补进来。

### 私有仓库注意事项

仓库创建时为私有，本次没有修改可见性。GitHub Free 的 Pages 要求公开仓库；保留私有仓库需要 GitHub Pro 等支持。GitHub Pro 与 ChatGPT Pro 不是同一订阅。

普通 Pages 网址通常公开可访问，**私有仓库不代表私有网站**。`noindex` 和 `robots.txt` 不是访问控制。不要在仓库或页面里保存个人日程、私密记录、完整课本、密码或令牌。

官方说明：https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

## 功能与保存边界

先回想英文，再翻开中文，自评认识 / 模糊 / 不认识。支持夜间/日间主题、隐藏真题提示、搜索、重看不熟词、保留位置及导入/导出。电脑可用空格翻面、1/2/3 自评、方向键翻页。发音仅使用设备已有的离线英语音色。

**词库统一在线更新，进度不自动跨设备同步。** 网站无登录或云端进度数据库，复习记录保存在当前浏览器 localStorage；无痕、清理数据或换浏览器可能丢失，请适时导出备份。

旧 HTML 的迁移：在旧页面导出 JSON，再在本站“来源与使用说明”中导入。支持 `night-vocab-2010t4` v1 和本站 `word-card` v2 记录，按时间合并，旧记录不覆盖新记录。网站和本地 HTML 不自动共享存储。

点击“检查更新”读取最新发布词库。更新不清空自评；正在做的一轮保留原卡片列表。更新后重新选择“本篇全部”即可看到新词。本站当前不提供离线缓存，首次打开与检查更新需要网络。

## 文件结构

- `index.html`：页面结构。
- `assets/app.css` / `assets/app.js`：样式与交互。
- `data/catalog.json`：篇目、词库版本、默认篇目。
- `data/decks/*.json`：词卡内容的唯一来源。
- `manifest.webmanifest` / `assets/icon.svg`：网站名称与图标。
- `.nojekyll` / `robots.txt`：静态发布和搜索引擎提示。
- `tools/validate.py`：无需第三方依赖的静态验证。
- `AGENTS.md`：后续更新约束。

## 以后更新

新篇目新增一个 `data/decks/*.json` 并登记到目录；已有篇目更新原文件。更新 `catalog.json` 的版本、日期和数量，不复制新网站。卡片 ID 保持稳定，同词同义项重现可复用 ID，不同义项用不同 ID。

页面代码变更时按需递增 index.html 中 app.js / app.css 的版本参数。单纯增加词汇不需要改页面代码或存储键。

## 本地预览和验证

```sh
python3 tools/validate.py
python3 -m http.server 8000
```

打开 http://localhost:8000/ 。因为词库已分离，不能直接双击 index.html。原有单文件 HTML 仍然可单独使用。

详细测试结果见 `QA.md`。词表原释义和题目片段保留来源，未为第三方资料授予再分发许可。
