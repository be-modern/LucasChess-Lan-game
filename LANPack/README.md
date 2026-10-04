# LucasChessR 局域网联机拓展包

给 LucasChessR 加上**局域网联机对局**功能：两台电脑各开一份 LucasChessR，一台建主机、一台加入，就能隔着网络下一盘棋（带棋钟、认输、提和）。

## 特点

- **纯增量安装**：不修改、不替换原版任何文件，随时可一键卸载。
- **零依赖**：只用 PySide6 自带的 `QtNetwork`，不需要装任何新库。
- **自动发现**：用 UDP 广播自动列出局域网里已经建好的对局，也支持手动填 IP。
- **棋钟同步**：主机设定的时间控制（分钟 + 每步加秒）自动同步给对手。
- **完整对局流程**：走子同步、认输、提和/接受/拒绝、对手掉线提示。
- **棋盘方向固定**：始终以你的颜色在下方，轮到对手时棋盘自动锁定。
- **网络聊天室**：联机界面里就能和局域网里所有人聊天，不用开局、不用连接
  （UDP 广播，复用 46218，**不需要额外放行端口**）。
- **对局私聊**：开局后聊天栏默认**停靠在棋盘左侧**（不挡棋盘），可一键切换成
  独立浮窗；和对手点对点聊天，浮窗关掉只是隐藏，对手发消息时会自动弹回来。

## 安装

1. 把整个 `LANPack` 文件夹复制到 LucasChessR 目录里（和 `bin`、`Resources` 同级），
   或者直接双击运行 `install.bat` 并把 LucasChessR 目录作为参数传给它：

   ```
   install.bat "C:\Games\LucasChessR"
   ```

2. 脚本会做两件事：
   - 复制 `Code\LAN\`（新增的联机模块）到 `LucasChessR\bin\Code\LAN\`；
   - 复制 `Code\Menus\PlayMenu.py` 到 `LucasChessR\bin\Code\Menus\`，
     这个文件会先加载原版的 `PlayMenu.pyc`，再往「Play（对局）」菜单里追加一条
     **Play on the local network (LAN)**。

3. **两台电脑都要装这个拓展包。**

## 使用

1. 两台电脑连到同一个局域网。
2. A 机：菜单 **Play → Play on the local network (LAN)**，选
   *Create a game*，填昵称、端口（默认 46217）、你执白/黑/随机、是否限时，点 Accept。
   程序会显示本机 IP，并开始等待对手。
3. B 机：同样菜单，选 *Join a game*，在列表里双击搜到的对局（或手动填 A 机的 IP），
   点 Accept 即可连上。
4. Windows 防火墙第一次会弹窗，请**允许**（专用网络/家庭网络）。
   需要在防火墙里放行 TCP 46217 与 UDP 46218（端口可在界面上改）。

对局中和普通的人人对局完全一样：走子、认输、提和按钮都在工具栏上。

### 聊天

- **全局（网络聊天室）**：打开联机界面后，底部就是聊天栏。局域网里所有
  打开了这个界面的人都能看到彼此的消息，昵称跟随界面上的「Your name」。
  关掉界面即退出聊天室。
- **对局中**：开局后聊天栏默认停在棋盘左侧，标题为 **Chat with <对手名>**，
  右上角按钮可切成独立浮窗。消息走已建立的 TCP 连接；浮窗关掉只是隐藏，
  对手再来消息会自动弹出。

## 卸载

```
uninstall.bat "C:\Games\LucasChessR"
```

只会删除本拓展包新增的文件：`bin\Code\LAN\`、`bin\Code\Menus\PlayMenu.py`
（如曾备份原版 `PlayMenu.py.lanbak`，会自动还原）。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `Code/LAN/protocol.py` | 换行分隔的 JSON 报文协议 |
| `Code/LAN/net.py` | TCP 传输（`QTcpServer` / `QTcpSocket` + Qt 信号） |
| `Code/LAN/discovery.py` | UDP 广播的建主机广播 / 搜对局 |
| `Code/LAN/manager.py` | `ManagerPlayLAN`：继承原版 `ManagerPlayHuman`，把「旁边坐着的人」换成「网络那头的人」 |
| `Code/LAN/wizard.py` | 建主机 / 加入 / 等待对手的对话框（含网络聊天室） |
| `Code/LAN/chat.py` | 聊天控件 `ChatPanel`、停靠/浮窗管理 `ChatDock`、非模态 `ChatWindow`、UDP 网络聊天室 `LanChatRoom` |
| `Code/LAN/hook.py` | 向 Play 菜单注入新选项 |
| `Code/Menus/PlayMenu.py` | 入口钩子：加载原版 `PlayMenu.pyc` 后调用 `hook.install()` |

## 工作原理

原版 LucasChessR 是编译后分发的（只有 `.pyc`，没有 `.py`）。拓展包利用了
Python 的一条规则：**同一目录下 `.py` 优先于 `.pyc`**。于是新增的
`Code/Menus/PlayMenu.py` 会先 `exec` 原版 `PlayMenu.pyc`（行为完全一致），
再给 `PlayMenu` 类打一个补丁：重写 `add_options()` 追加一条菜单项，并加上
`lan()` 方法。原版文件一个字节都没动，删掉这个 `.py` 就回到原版。

对局管理器则直接继承 `ManagerPlayHuman`：

- 轮到自己 → 调用父类的 `play_human()`，棋盘正常接受输入；
- 轮到对手 → 启动对手的棋钟、锁定棋盘、等待网络报文；
- 收到对手走子 → 通过标准的 `player_has_moved_dispatcher()` 回放，
  于是棋钟、箭头、声音、PGN 记录全部照常工作；
- 自己走子 → 在标准流程之后把 UCI 走法发给对手。

## 已知限制

- 联机对局不支持「悔棋」和「重新开始」（会让双方棋盘不同步），这两个按钮已移除。
- 不支持断线重连，掉线即结束对局。
- 双方 LucasChessR 版本建议保持一致。
