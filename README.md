# Eaglercraft-Pokemon-Offline

全程离线断网可部署的 Eaglercraft（网页版 Minecraft）+ 宝可梦玩法一体化服务端。

- 无需任何在线依赖：更新检查、证书下载、皮肤下载、在线服务器列表、语音/STUN 均已在配置中关闭
- 内置精简 JDK 17 运行库（`server/jre`），目标机器**无需预装 Java**
- 内置本地签名证书（`server/plugins/EaglercraftXServer/eagcert/backup.cert`）
- 网页客户端已做离线化处理，单文件自包含

## 目录结构

```
├── server/            服务端（Paper 1.12.2 + EaglercraftXServer + 宝可梦插件）
│   ├── jre/           内置 JDK 17 运行库（无需外部安装 Java）
│   ├── plugins/       插件（EaglerXServer / PokeServer / ViaVersion 等）
│   ├── world/         已生成的世界
│   ├── start.sh       启动脚本（2G 内存，自动用内置 JRE）
│   ├── start_lowmem.sh 低内存启动（768M，自动用内置 JRE）
│   ├── run.sh         Linux/macOS 一键启动（2G，G1GC，自动用内置 JRE）
│   └── run.bat        Windows 一键启动（2G，G1GC，自动用内置 JRE）
├── web/               离线网页客户端（单文件，自包含）
├── poke-plugin/       宝可梦插件源码（Java）
└── tools/ 脚本        clean_comments.py / offline_client_update.py / http_static.py
```

## 部署步骤（全程离线）

### 1. 启动服务端

Linux / macOS：

```bash
cd server
./start_lowmem.sh        # 低内存模式（768M），机器内存充足可用 ./start.sh
```

Windows：双击 `server/run.bat`。

服务端默认监听：
- `25565`：游戏 / Eaglercraft WebSocket 端口
- `25575`：RCON 端口（密码 `pokeserver`，如不需要可在 `server.properties` 关闭）

启动成功会出现 `Done (2s)!`，并加载本地证书 `backup.cert`。

### 2. 打开网页客户端

用浏览器打开 `web/index.html`（或任选 `web/` 下其它离线客户端 HTML）。

> 如需局域网内其它设备访问，可将 `web/` 目录用任意静态服务器托管，例如：
>
> ```bash
> python3 http_static.py        # 或 python3 -m http.server 8080 --directory web
> ```

### 3. 加入服务器

在客户端主菜单选择“多人游戏 / Multiplayer”，添加服务器并填写：

```
ws://<服务端IP>:25565
```

同一局域网内的玩家打开同一个客户端页面，填入相同的地址即可联机。

## 默认配置

- 游戏模式：生存（`server.properties` 可改）
- 白名单：关闭
- 宝可梦：野生刷新、精灵球、捕捉、队伍、进化等玩法（`/poke` 查看帮助）
- 服务器名：`宝可梦服 Pokemon Server`

## 说明

- 依赖环境（JDK、插件、证书、世界数据）均已内置，下载解压后断网即可运行
- 客户端若提示更新服务，可忽略；已默认关闭更新检查
- 如需清空存档重开，删除 `server/world*` 目录后重启即可
