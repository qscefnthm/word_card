# HarmonyOS 原生英语 TTS Probe

这是一个**独立实验**，不改动词卡站生产页面。

目标：直接在华为 HarmonyOS 真机上试听 Core Speech Kit 的英语离线音色，判断它是否值得用作词卡站的原生发音后端。

## 为什么做这个 Probe

普通 H5 的 `speechSynthesis` 在 HarmonyOS 浏览器 / ArkWeb 上并不可靠；而 Core Speech Kit 是原生 ArkTS 能力。官方资料显示：

- TTS 支持中文和英文。
- 英语推荐语言代码为 `en-US`。
- 英语音色 `person = 8` 为 **Laura（劳拉）女声**，需要下载。
- 当前 TTS 模式参数 `online = 1` 表示离线模式；在线模式目前不支持。
- 可通过 `listVoices` 查询音色状态，通过 `downloadVoice` 下载，再用 `createEngine` + `speak` 播放。
- 官方示例要求华为标准系统设备；最新样例注明 HarmonyOS 5.0.0 Release+，DevEco Studio 6.0.0 Release+，HarmonyOS SDK 6.0.0 Release+。
- 音色下载/status 能力从 5.1.1(19) 开始提供。

## 最快测试方式

1. 在 DevEco Studio 新建一个最简单的 Stage Model ArkTS Phone 项目。
2. 用本目录的 `Index.ets` 替换 `entry/src/main/ets/pages/Index.ets`。
3. 使用真机运行，不要用模拟器判断最终声音。
4. 依次点击：
   - **1. 检测英文音色**
   - 如果状态是 `GA`，点 **2. 下载 Laura**
   - 下载完成后点 **3. 初始化 Laura**
   - 点 **4. 播放考研词样例**
5. 试听：
   - alternative
   - gratification
   - procreation
   - subconscious
   - in retrospect

如果声音自然度明显优于当前站内 eSpeak，就可以继续做一个极薄的 HarmonyOS 壳：ArkWeb 继续加载现有词卡站，网页点击喇叭时通过 JS Bridge 调 Core Speech Kit。

## 预期错误

- `1002300002`: 英文语言不支持（先看 listVoices 返回）
- `1002300003`: 音色不支持
- `1002300008`: 音色下载失败
- `1002300010`: 音色已经下载过，不是坏事，直接初始化即可

## 不做的事

这个实验分支不会：
- 修改现有 GitHub Pages；
- 删除当前站内 MP3；
- 改动原词卡数据和复习进度。

只有真机试听结果确认够好后，才考虑把它接到正式词卡体验里。
