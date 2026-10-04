# LucasChessR LAN 联机拓展包

给经典国际象棋程序 [LucasChessR](https://github.com/lukasmonk/lucaschessR6) 加上**局域网（LAN）直连对局**：两台电脑各装一份，一台建主机、一台加入，就能隔着网络下一盘棋（带棋钟、认输、提和、聊天）。

- 🌐 **零服务器**：不经任何第三方，数据只在两台设备间传输
- ⚡ **纯增量安装**：不修改原版任何文件，一键卸载
- 🎮 **即开即玩**：UDP 自动发现房间，也支持手动填 IP

---

## 快速开始

1. 下载本仓库（或 Clone），得到 `LANPack/` 文件夹
2. 把 `LANPack/` 复制到 LucasChessR 目录里（和 `bin`、`Resources` 同级），
   或运行 `install.bat "C:\Games\LucasChessR"`
3. **两台电脑都要装**，然后按下面的方式联机：
   - **A 机（主机）**：菜单 `Play → Play on the local network (LAN)`，选 *Create a game*，填昵称/端口/执子颜色/限时 → Accept，等待对手
   - **B 机（加入）**：同样菜单选 *Join a game*，双击搜到的对局（或填 A 机 IP）→ Accept
4. Windows 防火墙首次弹窗请**允许**（放行 TCP 46217 与 UDP 46218，端口可在界面上改）

> 完整说明（功能特点、聊天、卸载、工作原理、已知限制）见 **[LANPack/README.md](LANPack/README.md)**。

---

## 获取原版 LucasChessR

本仓库**只包含拓展包**，不包含 LucasChessR 本体。请从上游项目获取原版：

- 源码：<https://github.com/lukasmonk/lucaschessR6>
- 官方发布：原项目的 Releases 页面

把原版装好后，再把本拓展包复制进去即可。

---

## ⚖️ 版权与许可

本项目是 [lukasmonk/lucaschessR6](https://github.com/lukasmonk/lucaschessR6) 的衍生作品（Derived Work）。

- **上游版权**归原作者 [lukasmonk](https://github.com/lukasmonk) 及原项目贡献者所有。
- **本拓展包**受 **GNU GPL v2（或更高版本）** 约束，任何人均可免费使用、修改、分享，但不得以闭源或专有许可形式发布。
- 完整协议文本见仓库根目录的 `LICENSE`。

---

## 📌 关于本仓库的范围

本仓库**只维护拓展包**（`LANPack/`）及其文档。以下内容属于本地开发/测试/运行时产物，**已通过 `.gitignore` 排除，现在和将来都不会上传**：

- 原版 LucasChessR 的打包副本（体积巨大、版权归上游）
- 测试副本 `LucasChessR-P2/`
- 开发/测试脚本 `_devtools/`
- 快照备份 `_snapshots/`
- 工作记忆 `.workbuddy/`
- 各种日志与 `__pycache__/`

---

## 🙏 致谢

本拓展包依赖原作者的卓越工作和开源精神。喜欢的话请去原项目点个 ⭐：<https://github.com/lukasmonk/lucaschessR6>

> **免责声明**：本拓展包为社区爱好者制作，非原项目官方版本。使用中遇到问题欢迎提交 Issue。
