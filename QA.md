# 验证与交付状态

## 远端状态

- 已通过 GitHub 连接读取 `qscefnthm/word_card`，确认其为私有空仓库，Pages 未开启。
- 首次尝试创建 README.md 被平台安全检查拦截。没有成功提交，不声称已上线，也没有改动仓库可见性。
- 没有绕过拦截，没有用其他传输方式写入远端。

## 已完成验证

1. `python3 tools/validate.py`：1 个正式篇目、32 张词卡、项目相对路径与来源字段通过。
2. `node --check assets/app.js`：JavaScript 语法通过。
3. 与原始 HTML 对比：32 张卡的 ID、词条、词表释义及编号/页码、原文、语境义、译文、分组等逐项一致。仅将一处带个人错题经历的提示改为一般用法提示，以及将 readingSource 中的个人截图表述改为试卷页码。
4. Chromium 离线组件测试：25 项通过，未观察到 JavaScript 运行时异常。桌面视口 1440×1000；手机视口 390×844。正面和展开答案均无横向溢出。

## 测试边界（重要）

当前环境阻止浏览器导航，返回 ERR_BLOCKED_BY_ADMINISTRATOR。因此没有关闭浏览器安全策略，而是使用纯本地 DOM/组件测试：从内存提供 HTML/CSS/JS，模拟 fetch 返回的 JSON 和 Storage。它验证交互、序列化/恢复、旧版导入、版本更新与错误分支，不代表已经在真实公网地址测试过。

**尚未验证：真实 GitHub Pages 部署、公网 HTTP 访问、网络环境下 CSP/资源加载、真实浏览器跨重启持久化、具体手机上的离线语音。** 上线后需补充这些检查。没有自动跨设备同步或离线缓存功能。

## 离线组件检查

1. PASS — Original 32 cards and 10 core cards load
2. PASS — Starts with sympathy; answer concealed
3. PASS — Rating cannot precede reveal
4. PASS — Reveals meaning and real reference ID
5. PASS — Rating advances and counts exactly once
6. PASS — Restores serialized position/theme/context (mock Storage)
7. PASS — Search uses Chinese meanings but answers remain concealed
8. PASS — Unfamiliar-only pack filters correctly
9. PASS — Last answer completes round
10. PASS — Export payload retains real self-rating
11. PASS — Legacy import merges without overwriting newer rating
12. PASS — Skipping does not count as studied
13. PASS — Update preserves ratings and running round snapshot
14. PASS — New cards appear when starting a full round
15. PASS — Failed update keeps already loaded cards
16. PASS — Retry recovers from failed update
17. PASS — New deck loads and shares stable term ratings
18. PASS — Each deck retains its own round position
19. PASS — Separate browser begins independently; no cloud-sync claim
20. PASS — Mobile front has no horizontal overflow
21. PASS — Mobile answer has no horizontal overflow
22. PASS — Mobile touch self-rating advances
23. PASS — Storage failure visibly disclosed
24. PASS — Study remains usable on storage failure
25. PASS — No JavaScript runtime errors

## 复现组件测试

先安装 Playwright 和 BeautifulSoup4，并按 Playwright 说明安装 Chromium，然后运行：

```sh
python3 tools/test_components.py
```

测试使用内存模拟，不访问外网，也不会把测试篇目写入正式词库。截图与 JSON 结果输出到 test-results/（已在 .gitignore 中忽略）。
