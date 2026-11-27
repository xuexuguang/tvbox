# TVBox&影视仓 配置聚合仓库
※ 部分配置纯自用，擅自拉取后果自负！

![配置状态](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2F58285474%2Ftvbox%2Fmain%2Foutput%2Fshield.json)
![更新频率](https://img.shields.io/badge/%E6%9B%B4%E6%96%B0-%E6%AF%8F%E5%A4%A9%203%20%E6%AC%A1-blue)

聚合 **肥猫、饭太硬、王二小、老刘备、小马、讴歌（欧歌）、4K小盒子、小盒子单仓、拾光多仓、挺好分享多仓** 等多个影视仓 / TVBox 单仓配置，通过 **GitHub Actions 定时自动更新**，并把结果直接提交回本仓库，供影视仓、TVBox、OK影视等软件随时拉取最新接口。

> 所有配置均来自互联网公开分享，版权归原作者所有；本仓库仅做聚合与镜像，仅供学习交流，请勿商用。

---

## 一、源可用性状态

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-27 11:09:36（北京时间） · 成功 **17/17** 个源

| 配⁠置⁠源 | 状⁠态 | 请⁠求⁠耗⁠时⁠（⁠m⁠s⁠） | 使⁠用⁠地⁠址 |
| --- | --- | ---: | --- |
| 饭太硬 | ✅ 成功 | — | [打开地址](<http://www.xn--sss604efuw.net/tv>)（JPEG解包） |
| 王二小 | ✅ 成功 | — | [打开地址](<https://d.kstore.dev/download/9280/wex.json>) |
| 老刘备 | ✅ 成功 | — | [打开地址](<https://raw.liucn.cc/box/m.json>) |
| 讴歌 | 📦 缓存 | — | 上次成功配置（本次更新未抓到，沿用缓存） |
| Easy | ✅ 成功 | — | [打开地址](<https://15318.kstore.space/easytv.jpg>) |
| 小盒子单仓 | ✅ 成功 | — | [打开地址](<http://xhztv.top/xhz/>) |
| 嗷呜线路 | ✅ 成功 | — | [打开地址](<https://9763.kstore.vip/aowu.json>) |
| 🚀盒子迷 | ✅ 成功 | — | [打开地址](<https://xn--i8sz35d1yr.top/%E7%A6%81%E6%AD%A2%E8%B4%A9%E5%8D%96>) |
| 🚀dxawi线路 | ✅ 成功 | — | [打开地址](<https://dxawi.github.io/0/0.json>) |
| 🙀小何线路 | ✅ 成功 | — | [打开地址](<https://jihulab.com/z-blog/xh2/-/raw/main/t.json>) |
| QIST自用 | ✅ 成功 | — | [打开地址](<https://raw.githubusercontent.com/qist/tvbox/master/jsm.json>) |
| QIST潇洒 | ✅ 成功 | — | [打开地址](<https://raw.githubusercontent.com/qist/tvbox/master/xiaosa/api.json>) |
| 东篱线路 | ✅ 成功 | — | [打开地址](<https://raw.githubusercontent.com/chitue/dongliTV/main/api.json>) |
| 无名 | ✅ 成功 | — | [打开地址](<https://6800.kstore.vip/fish.json>) |
| noimank | ✅ 成功 | — | [打开地址](<https://gitlab.com/noimank/tvbox/-/raw/main/tvbox1.json>) |
| FongMi专版 | ✅ 成功 | — | [打开地址](<https://www.252035.xyz/z/FongMi.json>) |
| 备用·tvyuan全量 | ✅ 成功 | — | [打开地址](<https://tv.cc0cd.cc.cd/>) |
<!-- STATUS_END -->

## 二、仓库结构

```
tvbox/
├── .github/workflows/update.yml   # GitHub Actions 自动更新工作流
├── config/sources.json            # 配置源列表（主地址 + 备用地址），可自行增删改
├── scripts/
│   ├──update.py
│   └──tsjm.py                      # 核心更新脚本（下载→校验→合并→落盘→更新状态）
├── output/                         # 更新产物（由脚本自动生成并提交）
│   ├── 多仓订阅.json                 # 多仓聚合订阅（推荐，App 内可切换各源）
│   ├── 单仓聚合.json                 # 单仓聚合（所有源 sites 合并成一个，开箱即用）
│   ├── shield.json                 # shields.io 状态徽章数据
│   ├── status.json                 # 各源更新状态（机器可读）
│   ├── feimao.json / fantaiying.json / ...  # 各源独立配置
│   └── ...
├── requirements.txt
└── README.md
```

## 三、在影视仓 / TVBox 中使用

国内网络优先使用以下加速地址。多仓链接填入 App 的「多仓／订阅」，单仓链接填入「配置地址」。

<!-- ACCELERATED_LINKS_START -->

| 类⁠型 | 加⁠速⁠地⁠址 | 数⁠量 |
| --- | --- | ---: |
| **多仓订阅（推荐）** | [打开加速地址](<https://gh-proxy.org/https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/%E5%A4%9A%E4%BB%93%E8%AE%A2%E9%98%85.json>) | 17 条线路 |
| **单仓聚合** | [打开加速地址](<https://gh-proxy.org/https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/%E5%8D%95%E4%BB%93%E8%81%9A%E5%90%88.json>) | 2816 个站点 |

<!-- ACCELERATED_LINKS_END -->

直连 GitHub 时可使用以下地址：

| 类⁠型 | 地⁠址 | 说⁠明 |
| --- | --- | --- |
| **多仓订阅（推荐）** | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/%E5%A4%9A%E4%BB%93%E8%AE%A2%E9%98%85.json>) | App 内可在各源之间切换 |
| **单仓聚合** | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/%E5%8D%95%E4%BB%93%E8%81%9A%E5%90%88.json>) | 所有源站点合并成一个，无需切换 |

各线路的直连地址随多仓订阅同步更新。

<!-- SOURCE_LINKS_START -->

| 线⁠路 | 直⁠连⁠地⁠址 | 站⁠点⁠数⁠（⁠过⁠滤⁠后⁠） |
| --- | --- | ---: |
| 线路 · 饭太硬 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/fantaiying.json>) | 33 |
| 线路 · 王二小 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/wangerxiao.json>) | 71 |
| 线路 · 老刘备 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/laoliubei.json>) | 197 |
| 线路 · 讴歌 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/ouge.json>) | 4 |
| 线路 · Easy | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/easy.json>) | 99 |
| 线路 · 小盒子单仓 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/xiaohezi.json>) | 42 |
| 线路 · 嗷呜线路 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/aowu.json>) | 66 |
| 线路 · 🚀盒子迷 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/hezimi.json>) | 18 |
| 线路 · 🚀dxawi线路 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/dxawi.json>) | 33 |
| 线路 · 🙀小何线路 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/xiaohe.json>) | 60 |
| 线路 · QIST自用 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/qist.json>) | 119 |
| 线路 · QIST潇洒 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/qist-xiaosa.json>) | 81 |
| 线路 · 东篱线路 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/dongli.json>) | 53 |
| 线路 · 无名 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/fish.json>) | 92 |
| 线路 · noimank | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/noimank.json>) | 54 |
| 线路 · FongMi专版 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/fongmi.json>) | 31 |
| 线路 · 备用·tvyuan全量 | [打开直连](<https://raw.githubusercontent.com/xuexuguang/tvbox/main/output/tvyuan.json>) | 1239 |

<!-- SOURCE_LINKS_END -->

> 更新脚本根据 `GITHUB_REPOSITORY` 生成多仓订阅里的线路地址。GitHub 和第三方加速代理均可能缓存响应，更新后可等待几分钟再在 App 内刷新订阅。

## 四、自动更新机制

- 推送后，GitHub 自动识别 `.github/workflows/update.yml`。
- 默认每天自动更新三次，分别在北京时间 **03:00、11:00 和 17:00**（UTC 03:00、09:00 和 19:00）。
- 也可在 **Actions → Auto Update TVBox Configs → Run workflow** 手动触发。
- 更新结果自动提交回 `main` 分支，README 状态表与徽章同步刷新。
- 工作流使用内置 `GITHUB_TOKEN`，无需配置任何密钥。

## 五、自定义配置源

编辑 `config/sources.json` 即可增删配置源或更换地址：

```json
{
  "id": "mysource",
  "name": "我的源",
  "urls": [
    "https://example.com/tv",
    "https://backup.example.com/tv"
  ]
}
```

- `id`：输出文件名（建议英文小写）。
- `name`：在多仓订阅与状态表中展示的名字。
- `urls`：依次尝试的地址列表，第一个成功的会被使用；可按"主地址在前、备用在后"排列。
- 修改后推送到 `main` 分支即会自动触发一次更新。

### 站点过滤

在 `config/site_filter.jsonc` 中填写 `exclude_keys` 或 `exclude_names`。两项均可省略，默认是空数组。按站点原始 `key` 或完整 `name` 精确匹配，命中任意一项即过滤。

`config/site_filter.jsonc` 支持 `//` 单行注释。可以写在条目后面，例如 `"MDrive", // 我的云盘配置`。数组最后一项省略逗号。

配置生效后，单仓聚合、单独线路和多仓订阅共用规则。多仓里的子仓会抓取并生成本站的配置链接。抓取失败时尝试上次的原始缓存，缺少缓存的子仓会从本次订阅中省略。清空规则后，下次更新恢复原来的上游订阅方式。

运行 `python3 scripts/update.py` 或等待 GitHub Actions 更新产物后，在播放器里刷新订阅。

## 六、本地手动更新（可选）

```bash
python3 -m pip install -r requirements.txt
python3 scripts/update.py
```

## 七、脚本特性

- **中文域名自动转 punycode**：`饭太硬.com` → `xn--sss604efuw.com`，避免 DNS 解析失败。
- **多地址回退**：每个源按顺序尝试主/备用地址，单个地址失败不影响其他源。
- **并发抓取**：常规源最多同时抓取 4 条，订阅和状态表仍按配置顺序生成。
- **智能重试**：仅对超时、连接错误、空响应等瞬态问题退避重试；4xx/5xx 等确定性失败直接跳过。
- **兼容多仓订阅**：既支持单仓（含 sites 字段），也支持多仓订阅（顶层 urls 数组）格式。
- **反爬兼容**：使用简洁 UA（部分接口对完整浏览器 UA 下发挑战页），自动剔除 JSON 内嵌的 `//` 注释，兼容未转义控制字符。
- **聚合单仓**：把所有成功源的 `sites` 按 key 去重合并（重复 key 自动加源前缀），`lives/parses` 等列表合并去重。
- **状态可视化**：每次更新自动刷新 README 状态表与 shields.io 徽章。
- **部分成功可用**：只要有一个源成功就产出可用订阅，失败源记录在 `status.json` 与 README 状态表。

## 八、常见问题

- **某个源一直失败？** 大部分源做了地区/频率限制，GitHub Actions 与本地网络环境不同，可能某个环境能访问、另一个不能。脚本会按 `urls` 顺序自动尝试所有备用地址，只把成功的写入。
- **自动提交会不会死循环？** 不会。push 触发只监听 `config/`、`scripts/`、`requirements.txt` 的变更，自动提交只改 `output/` 与 README 状态区，不会再次触发。

## 九、免责声明

本项目仅用于学习、测试与个人使用；聚合的接口资源来自互联网公开分享，版权归原作者所有。若涉及侵权，请联系删除相应内容。
