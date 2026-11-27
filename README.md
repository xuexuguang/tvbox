# TVBox 与影视仓订阅

聚合 TVBox 和影视仓配置，定时检测源并生成多仓订阅与单仓聚合。

[更新工作流](.github/workflows/update.yml) · [源清单](config/sources.json) · [站点过滤](config/site_filter.jsonc)

## 打开管理页

在线入口是 [TVBox 源管理](https://xuexuguang.github.io/tvbox/manage/)。首次发布前，在仓库的 **Settings → Pages → Source** 选择 **GitHub Actions**。更新工作流生成订阅后会一并部署管理页和订阅文件。

需要在本地测试源时，在仓库根目录运行以下命令。

```bash
python3 -m pip install -r requirements.txt
python3 scripts/manage_server.py
```

**[打开 TVBox 源管理](http://127.0.0.1:8765/manage/)**

在页面上查看各源状态和延迟、测试单条源，或复制订阅地址。增删改需要具有仓库写权限的 GitHub 令牌。

## 维护配置

| 想做什么 | 在哪里改 |
| --- | --- |
| 添加源、调整主备地址 | [源清单](config/sources.json)。地址按填写顺序尝试。 |
| 从订阅中排除站点 | [站点过滤](config/site_filter.jsonc)。按站点 `key` 或完整名称匹配。 |

提交源清单到 `main` 会触发更新。[GitHub Actions](.github/workflows/update.yml) 也会在每天 **03:00、11:00、17:00（北京时间）** 定时运行，支持手动触发。

本地可运行 `python3 scripts/update.py`，生成结果写入 `outout_local/`。

---

配置来自公开分享，仅供学习与个人使用，请勿商用。
