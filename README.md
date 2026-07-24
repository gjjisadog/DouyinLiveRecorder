![video_spider](https://socialify.git.ci/ihmily/DouyinLiveRecorder/image?font=Inter&forks=1&language=1&owner=1&pattern=Circuit%20Board&stargazers=1&theme=Light)

## 💡简介
[![Python Version](https://img.shields.io/badge/python-3.11.6-blue.svg)](https://www.python.org/downloads/release/python-3116/)
[![Supported Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux-blue.svg)](https://github.com/ihmily/DouyinLiveRecorder)
[![Docker Pulls](https://img.shields.io/docker/pulls/ihmily/douyin-live-recorder?label=Docker%20Pulls&color=blue&logo=docker)](https://hub.docker.com/r/ihmily/douyin-live-recorder/tags)
![GitHub issues](https://img.shields.io/github/issues/ihmily/DouyinLiveRecorder.svg)
[![Latest Release](https://img.shields.io/github/v/release/ihmily/DouyinLiveRecorder)](https://github.com/ihmily/DouyinLiveRecorder/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/ihmily/DouyinLiveRecorder/total)](https://github.com/ihmily/DouyinLiveRecorder/releases/latest)

一款**简易**的可循环值守的直播录制工具，基于FFmpeg实现多平台直播源录制，支持自定义配置录制以及直播状态推送。

</div>

## 😺已支持平台

- [x] 抖音
- [x] TikTok
- [x] 快手
- [x] 虎牙
- [x] 斗鱼
- [x] YY
- [x] B站
- [x] 小红书
- [x] bigo 
- [x] blued
- [x] SOOP(原AfreecaTV)
- [x] 网易cc
- [x] 千度热播
- [x] PandaTV
- [x] 猫耳FM
- [x] Look直播
- [x] WinkTV
- [x] TTingLive(原Flextv)
- [x] PopkonTV
- [x] TwitCasting
- [x] 百度直播
- [x] 微博直播
- [x] 酷狗直播
- [x] TwitchTV
- [x] LiveMe
- [x] 花椒直播
- [x] 流星直播
- [x] ShowRoom
- [x] Acfun
- [x] 映客直播
- [x] 音播直播
- [x] 知乎直播
- [x] CHZZK
- [x] 嗨秀直播
- [x] vv星球直播
- [x] 17Live
- [x] 浪Live
- [x] 畅聊直播
- [x] 飘飘直播
- [x] 六间房直播
- [x] 乐嗨直播
- [x] 花猫直播
- [x] Shopee
- [x] Youtube
- [x] 淘宝
- [x] 京东
- [x] Faceit
- [x] 咪咕
- [x] 连接直播
- [x] 来秀直播
- [x] Picarto
- [ ] 更多平台正在更新中

</div>

## 🧩客户端当前已迁移平台（2026-04-01）

- 本节仅描述 `client/` PySide6 客户端当前已接入的范围，**不等同于**上方旧版主程序 / CLI 的完整平台清单。
- 当前已接入 `client/core/platform_router.py` 与 `client/core/stream_resolver.py` 的客户端平台为：
  - 抖音、TikTok、快手、虎牙、斗鱼、YY、B站、网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK
  - 以及自定义 `m3u8` / `flv` 直链录制
- 当前已确认的客户端自动化验证范围：
  - 路由识别：网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK
  - 解析分支：网易 CC、CHZZK
  - 任务导入 / 展示 / 持久化：抖音、TikTok、快手、ShowRoom、CHZZK
  - 录制链路烟测：自定义 `m3u8` 直链
- 如需继续补齐“客户端已验证平台矩阵”，请优先查看 `docs/handover/executable_backlog.md` 与 `docs/sessions/2026-04-01-platform-coverage-bl005.md`。

## 🎈项目结构

```
.
└── DouyinLiveRecorder/
    ├── /config -> (config record)
    ├── /logs -> (save runing log file)
    ├── /backup_config -> (backup file)
    ├── /douyinliverecorder -> (package)
        ├── initializer.py-> (check and install nodejs)
    	├── spider.py-> (get live data)
    	├── stream.py-> (get live stream address)
    	├── utils.py -> (contains utility functions)
    	├── logger.py -> (logger handdle)
    	├── room.py -> (get room info)
    	├── ab_sign.py-> (generate dy token)
    	├── /javascript -> (some decrypt code)
    ├── main.py -> (main file)
    ├── ffmpeg_install.py -> (ffmpeg install script)
    ├── demo.py -> (call package test demo)
    ├── msg_push.py -> (send live status update message)
    ├── ffmpeg.exe -> (record video)
    ├── index.html -> (play m3u8 and flv video)
    ├── requirements.txt -> (library dependencies)
    ├── docker-compose.yaml -> (Container Orchestration File)
    ├── Dockerfile -> (Application Build Recipe)
    ├── StopRecording.vbs -> (stop recording script on Windows)
    ...
```

</div>

## 🌱使用说明

- 对于只想使用录制软件的小白用户，进入[Releases](https://github.com/ihmily/DouyinLiveRecorder/releases) 中下载最新发布的 zip压缩包即可，里面有打包好的录制软件。（有些电脑可能会报毒，直接忽略即可，如果下载时被浏览器屏蔽，请更换浏览器下载）

- 压缩包解压后，在 `config` 文件夹内的 `URL_config.ini` 中添加录制直播间地址，一行一个直播间地址。如果要自定义配置录制，可以修改`config.ini` 文件，推荐将录制格式修改为`ts`。
- 以上步骤都做好后，就可以运行`DouyinLiveRecorder.exe` 程序进行录制了。录制的视频文件保存在同目录下的 `downloads` 文件夹内。

- 另外，如果需要录制TikTok、AfreecaTV等海外平台，请在配置文件中设置开启代理并添加proxy_addr链接 如：`127.0.0.1:7890` （这只是示例地址，具体根据实际填写）。
- 建议把仓库里的 `config/config.example.ini`、`config/URL_config.example.ini` 作为公开样板；本地真实使用时复制为 `config/config.ini`、`config/URL_config.ini` 后再填写自己的 Cookie、推送 token、账号密码与直播间地址。
- `config/config.ini` 可能包含 Cookie、推送接口、SMTP 授权码、平台账号密码等敏感信息；共享仓库、截图或日志前请先脱敏。
- 如需校验公开样板没有落后于真实配置，可执行 `& '.\.client-conda-env\python.exe' scripts/check_config_examples.py`。

- 假如`URL_config.ini`文件中添加的直播间地址，有个别直播间暂时不想录制又不想移除链接，可以在对应直播间的链接开头加上`#`，那么将停止该直播间的监测以及录制。

- 软件默认录制清晰度为 `原画` ，如果要单独设置某个直播间的录制画质，可以在添加直播间地址时前面加上画质即可，如`超清，https://live.douyin.com/745964462470` 记得中间要有`,` 分隔。

- 如果要长时间挂着软件循环监测直播，最好循环时间设置长一点（咱也不差没录制到的那几分钟），避免因请求频繁导致被官方封禁IP 。

- 要停止直播录制，Windows平台可执行StopRecording.vbs脚本文件，或者在录制界面使用 `Ctrl+C ` 组合键中断录制，若要停止其中某个直播间的录制，可在`URL_config.ini`文件中的地址前加#，会自动停止对应直播间的录制并正常保存已录制的视频。
- 最后，欢迎右上角给本项目一个star，同时也非常乐意大家提交pr。

&emsp;

直播间链接示例：

```
抖音:
https://live.douyin.com/745964462470
https://v.douyin.com/iQFeBnt/
https://live.douyin.com/yall1102  （链接+抖音号）
https://v.douyin.com/CeiU5cbX  （主播主页地址）

TikTok:
https://www.tiktok.com/@pearlgaga88/live

快手:
https://live.kuaishou.com/u/yall1102

虎牙:
https://www.huya.com/52333

斗鱼:
https://www.douyu.com/3637778?dyshid=
https://www.douyu.com/topic/wzDBLS6?rid=4921614&dyshid=

YY:
https://www.yy.com/22490906/22490906

B站:
https://live.bilibili.com/320

小红书（直播间分享地址):
http://xhslink.com/xpJpfM

bigo直播:
https://www.bigo.tv/cn/716418802

buled直播:
https://app.blued.cn/live?id=Mp6G2R

SOOP:
https://play.sooplive.co.kr/sw7love

网易cc:
https://cc.163.com/583946984

千度热播:
https://qiandurebo.com/web/video.php?roomnumber=33333

PandaTV:
https://www.pandalive.co.kr/live/play/bara0109

猫耳FM:
https://fm.missevan.com/live/868895007

Look直播:
https://look.163.com/live?id=65108820&position=3

WinkTV:
https://www.winktv.co.kr/live/play/anjer1004

FlexTV(TTinglive)::
https://www.flextv.co.kr/channels/593127/live

PopkonTV:
https://www.popkontv.com/live/view?castId=wjfal007&partnerCode=P-00117
https://www.popkontv.com/channel/notices?mcid=wjfal007&mcPartnerCode=P-00117

TwitCasting:
https://twitcasting.tv/c:uonq

百度直播:
https://live.baidu.com/m/media/pclive/pchome/live.html?room_id=9175031377&tab_category

微博直播:
https://weibo.com/l/wblive/p/show/1022:2321325026370190442592

酷狗直播:
https://fanxing2.kugou.com/50428671?refer=2177&sourceFrom=

TwitchTV:
https://www.twitch.tv/gamerbee

LiveMe:
https://www.liveme.com/zh/v/17141543493018047815/index.html

花椒直播:
https://www.huajiao.com/l/345096174

流星直播:
https://www.7u66.com/100960

ShowRoom:
https://www.showroom-live.com/room/profile?room_id=480206  （主播主页地址）

Acfun:
https://live.acfun.cn/live/179922

映客直播:
https://www.inke.cn/liveroom/index.html?uid=22954469&id=1720860391070904

音播直播:
https://live.ybw1666.com/800002949

知乎直播:
https://www.zhihu.com/people/ac3a467005c5d20381a82230101308e9 (主播主页地址)

CHZZK:
https://chzzk.naver.com/live/458f6ec20b034f49e0fc6d03921646d2

嗨秀直播:
https://www.haixiutv.com/6095106

VV星球直播:
https://h5webcdn-pro.vvxqiu.com//activity/videoShare/videoShare.html?h5Server=https://h5p.vvxqiu.com&roomId=LP115924473&platformId=vvstar

17Live:
https://17.live/en/live/6302408

浪Live:
https://www.lang.live/en-US/room/3349463

畅聊直播:
https://live.tlclw.com/106188

飘飘直播:
https://m.pp.weimipopo.com/live/preview.html?uid=91648673&anchorUid=91625862&app=plpl

六间房直播:
https://v.6.cn/634435

乐嗨直播:
https://www.lehaitv.com/8059096

花猫直播:
https://h.catshow168.com/live/preview.html?uid=19066357&anchorUid=18895331

Shopee:
https://sg.shp.ee/GmpXeuf?uid=1006401066&session=802458

Youtube:
https://www.youtube.com/watch?v=cS6zS5hi1w0

淘宝(需cookie):
https://tbzb.taobao.com/live?liveId=532359023188
https://m.tb.cn/h.TWp0HTd

京东:
https://3.cn/28MLBy-E

Faceit:
https://www.faceit.com/zh/players/Compl1/stream

连接直播:
https://show.lailianjie.com/10000258

咪咕直播:
https://www.miguvideo.com/p/live/120000541321

来秀直播:
https://www.imkktv.com/h5/share/video.html?uid=1845195&roomId=1710496

Picarto:
https://www.picarto.tv/cuteavalanche
```

&emsp;

## 🎃源码运行
使用源码运行，前提要有**Python>=3.10**环境，如果没有请先自行安装Python，再执行下面步骤。

1.首先拉取或手动下载本仓库项目代码

```bash
git clone https://github.com/ihmily/DouyinLiveRecorder.git
```

2.进入项目文件夹，安装依赖

```bash
cd DouyinLiveRecorder
pip3 install -r requirements.txt
```

3.安装[FFmpeg](https://ffmpeg.org/download.html#build-linux)，如果是Windows系统，这一步可跳过。对于Linux系统，执行以下命令安装

CentOS执行

```bash
yum install epel-release
yum install ffmpeg
```

Ubuntu则执行

```bash
apt update
apt install ffmpeg
```

macOS 执行

**如果已经安装 Homebrew 请跳过这一步**

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

```bash
brew install ffmpeg
```

4.运行程序

```python
python main.py
```

其中Linux系统请使用`python3 main.py` 运行。

&emsp;
## 🐋容器运行

在运行命令之前，请确保您的机器上安装了 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/) 

1.快速启动

最简单方法是直接使用项目中的 [docker-compose.yaml](https://github.com/ihmily/DouyinLiveRecorder/blob/main/docker-compose.yaml) 文件。当前 Compose 默认会构建当前仓库代码，并使用固定版本标签：

```bash
docker compose up -d --build
```

Docker 部署默认会同时开启一个轻量配置页，浏览器访问 `http://localhost:18091` 即可直接增删、停用和批量编辑主播列表。

可选先复制 `.env.docker.example` 为 `.env`，覆盖镜像仓库名或版本标签：

```bash
cp .env.docker.example .env
```

如需修改网页端口，可在 `.env` 中设置：

```bash
DLR_WEB_PORT=18091
```

2.本地构建镜像(可选)

如果你只想在本地提前构建镜像，也可以直接执行：

```bash
docker build -t douyin-live-recorder:4.0.7 .
docker compose up -d
```

配置页默认同样监听 `18091` 端口；如果宿主机端口冲突，请同步修改 `.env` 里的 `DLR_WEB_PORT`。

3.buildx 多架构发布(可选)

仓库内已提供统一的多架构发布入口，镜像标签默认跟随 `client/version.py` 中的版本号：

PowerShell:

```powershell
.\build_docker_release.ps1 --repository ihmily/douyin-live-recorder --push
```

批处理:

```bat
build_docker_release.bat --repository ihmily/douyin-live-recorder --push
```

也可以直接调用 Python 模块，先预览 buildx 命令：

```bash
python -m client.infra.docker.release buildx --repository ihmily/douyin-live-recorder --push --dry-run
```

4.停止容器实例

```bash
docker compose stop
```



4.注意事项

①在docker容器内运行本程序之前，请先在配置文件中添加要录制的直播间地址。

②在容器内时，如果手动中断容器运行停止录制，会导致正在录制的视频文件损坏！

**无论哪种运行方式，为避免手动中断或者异常中断导致录制的视频文件损坏的情况，推荐使用 `ts` 格式保存**。

&emsp;

## 🤖相关项目

- StreamCap: https://github.com/ihmily/StreamCap
- streamget: https://github.com/ihmily/streamget

&emsp;

## ❤️贡献者

&ensp;&ensp; [![Hmily](https://github.com/ihmily.png?size=50)](https://github.com/ihmily)
[![iridescentGray](https://github.com/iridescentGray.png?size=50)](https://github.com/iridescentGray)
[![annidy](https://github.com/annidy.png?size=50)](https://github.com/annidy)
[![wwkk2580](https://github.com/wwkk2580.png?size=50)](https://github.com/wwkk2580)
[![missuo](https://github.com/missuo.png?size=50)](https://github.com/missuo)
<a href="https://github.com/xueli12" target="_blank"><img src="https://github.com/xueli12.png?size=50" alt="xueli12" style="width:53px; height:51px;" /></a>
<a href="https://github.com/kaine1973" target="_blank"><img src="https://github.com/kaine1973.png?size=50" alt="kaine1973" style="width:53px; height:51px;" /></a>
<a href="https://github.com/yinruiqing" target="_blank"><img src="https://github.com/yinruiqing.png?size=50" alt="yinruiqing" style="width:53px; height:51px;" /></a>
<a href="https://github.com/Max-Tortoise" target="_blank"><img src="https://github.com/Max-Tortoise.png?size=50" alt="Max-Tortoise" style="width:53px; height:51px;" /></a>
[![justdoiting](https://github.com/justdoiting.png?size=50)](https://github.com/justdoiting)
[![dhbxs](https://github.com/dhbxs.png?size=50)](https://github.com/dhbxs)
[![wujiyu115](https://github.com/wujiyu115.png?size=50)](https://github.com/wujiyu115)
[![zhanghao333](https://github.com/zhanghao333.png?size=50)](https://github.com/zhanghao333)
<a href="https://github.com/gyc0123" target="_blank"><img src="https://github.com/gyc0123.png?size=50" alt="gyc0123" style="width:53px; height:51px;" /></a>

&ensp;&ensp; [![HoratioShaw](https://github.com/HoratioShaw.png?size=50)](https://github.com/HoratioShaw)
[![nov30th](https://github.com/nov30th.png?size=50)](https://github.com/nov30th)
[![727155455](https://github.com/727155455.png?size=50)](https://github.com/727155455)
[![nixingshiguang](https://github.com/nixingshiguang.png?size=50)](https://github.com/nixingshiguang)
[![1411430556](https://github.com/1411430556.png?size=50)](https://github.com/1411430556)
[![Ovear](https://github.com/Ovear.png?size=50)](https://github.com/Ovear)
&emsp;

## ⏳提交日志

- 20251024
  - 修复抖音风控无法获取数据问题
  
  - 新增soop.com录制支持
  
  - 修复bigo录制
  
- 20250127
  - 新增淘宝、京东、faceit直播录制
  - 修复小红书直播流录制以及转码问题
  - 修复畅聊、VV星球、flexTV直播录制
  - 修复批量微信直播推送
  - 新增email发送ssl和port配置
  - 新增强制转h264配置
  - 更新ffmpeg版本
  - 重构包为异步函数！

- 20241130
  - 新增shopee、youtube直播录制
  - 新增支持自定义m3u8、flv地址录制
  - 新增自定义执行脚本，支持python、bat、bash等
  - 修复YY直播、花椒直播和小红书直播录制
  - 修复b站标题获取错误
  - 修复log日志错误
- 20241030
  - 新增嗨秀直播、vv星球直播、17Live、浪Live、SOOP、畅聊直播(原时光直播)、飘飘直播、六间房直播、乐嗨直播、花猫直播等10个平台直播录制
  - 修复小红书直播录制，支持小红书作者主页地址录制直播
  - 新增支持ntfy消息推送，以及新增支持批量推送多个地址（逗号分隔多个推送地址)
  - 修复Liveme直播录制、twitch直播录制
  - 新增Windows平台一键停止录制VB脚本程序
- 20241005
  - 新增邮箱和Bark推送
  - 新增直播注释停止录制
  - 优化分段录制
  - 重构部分代码
- 20240928
  - 新增知乎直播、CHZZK直播录制
  - 修复音播直播录制
- 20240903
  - 新增抖音双屏录制、音播直播录制
  - 修复PandaTV、bigo直播录制
- 20240713
  - 新增映客直播录制
- 20240705
  - 新增时光直播录制
- 20240701
  - 修复虎牙直播录制2分钟断流问题
  - 新增自定义直播推送内容
- 20240621
  - 新增Acfun、ShowRoom直播录制
  - 修复微博录制、新增直播源线路
  - 修复斗鱼直播60帧录制
  - 修复酷狗直播录制
  - 修复TikTok部分无法解析直播源
  - 修复抖音无法录制连麦直播
- 20240510
  - 修复部分虎牙直播间录制错误
- 20240508
  - 修复花椒直播录制
  - 更改文件路径解析方式 [@kaine1973](https://github.com/kaine1973)
- 20240506
  - 修复抖音录制画质解析bug
  - 修复虎牙录制 60帧最高画质问题
  - 新增流星直播录制
- 20240427
  - 新增LiveMe、花椒直播录制
- 20240425
  - 新增TwitchTV直播录制
- 20240424
  - 新增酷狗直播录制、优化PopkonTV直播录制
- 20240423
  - 新增百度直播录制、微博直播录制
  - 修复斗鱼录制直播回放的问题
  - 新增直播源地址显示以及输出到日志文件设置
- 20240311
  - 修复海外平台录制bug，增加画质选择，增强录制稳定性
  - 修复虎牙录制bug (虎牙`一起看`频道 有特殊限制，有时无法录制)
- 20240309
  - 修复虎牙直播、小红书直播和B站直播录制
  - 新增5个直播平台录制，包括winktv、flextv、look、popkontv、twitcasting
  - 新增部分海外平台账号密码配置，实现自动登录并更新配置文件中的cookie
  - 新增自定义配置需要使用代理录制的平台
  - 新增只推送开播消息不进行录制设置
  - 修复了一些bug
- 20240209
  - 优化AfreecaTV录制，新增账号密码登录获取cookie以及持久保存
  - 修复了小红书直播因官方更新直播域名，导致无法录制直播的问题
  - 修复了更新URL配置文件的bug
  - 最后，祝大家新年快乐！

<details><summary>点击展开更多提交日志</summary>

- 20240129
  - 新增猫耳FM直播录制
- 20240127
  - 新增千度热播直播录制、新增pandaTV(韩国)直播录制
  - 新增telegram直播状态消息推送，修复了某些bug
  - 新增自定义设置不同直播间的录制画质(即每个直播间录制画质可不同)
  - 修改录制视频保存路径为 `downloads` 文件夹，并且分平台进行保存。
- 20240114
  - 新增网易cc直播录制，优化ffmpeg参数，修改AfreecaTV输入直播地址格式
  - 修改日志记录器 @[iridescentGray](https://github.com/iridescentGray)
- 20240102
  - 修复Linux上运行，新增docker配置文件
- 20231210
  - 修复录制分段bug，修复bigo录制检测bug
  - 新增自定义修改录制主播名
  - 新增AfreecaTV直播录制，修复某些可能会发生的bug
- 20231207
  - 新增blued直播录制，修复YY直播录制，新增直播结束消息推送
- 20231206
  - 新增bigo直播录制
- 20231203
  - 新增小红书直播录制（全网首发），目前小红书官方没有切换清晰度功能，因此直播录制也只有默认画质
  - 小红书录制暂时无法循环监测，每次主播开启直播，都要重新获取一次链接
  - 获取链接的方式为 将直播间转发到微信，在微信中打开后，复制页面的链接。
- 20231030
  - 本次更新只是进行修复，没时间新增功能。
  - 欢迎各位大佬提pr 帮忙更新维护
- 20230930
  - 新增抖音从接口获取直播流，增强稳定性
  - 修改快手获取直播流的方式，改用从官方接口获取
  - 祝大家中秋节快乐！
- 20230919
  - 修复了快手版本更新后录制出错的问题，增加了其自动获取cookie(~~稳定性未知~~)
  - 修复了TikTok显示正在直播但不进行录制的问题
- 20230907
  - 修复了因抖音官方更新了版本导致的录制出错以及短链接转换出错
  - 修复B站无法录制原画视频的bug
  - 修改了配置文件字段，新增各平台自定义设置Cookie
- 20230903
  - 修复了TikTok录制时报644无法录制的问题
  - 新增直播状态推送到钉钉和微信的功能，如有需要请看 [设置推送教程](https://d04vqdiqwr3.feishu.cn/docx/XFPwdDDvfobbzlxhmMYcvouynDh?from=from_copylink)
  - 最近比较忙，其他问题有时间再更新
- 20230816
  - 修复斗鱼直播（官方更新了字段）和快手直播录制出错的问题
- 20230814
  - 新增B站直播录制
  - 写了一个在线播放M3U8和FLV视频的网页源码，打开即可食用
- 20230812
  - 新增YY直播录制
- 20230808
  - 修复主播重新开播无法再次录制的问题
- 20230807
  - 新增了斗鱼直播录制
  - 修复显示录制完成之后会重新开始录制的问题
- 20230805
  - 新增了虎牙直播录制，其暂时只能用flv视频流进行录制
  - Web API 新增了快手和虎牙这两个平台的直播流解析（TikTok要代理）
- 20230804
  - 新增了快手直播录制，优化了部分代码
  - 上传了一个自动化获取抖音直播间页面Cookie的代码，可以用于录制
- 20230803
  - 通宵更新 
  - 新增了国际版抖音TikTok的直播录制，去除冗余 简化了部分代码
- 20230724	
  - 新增了一个通过抖音直播间地址获取直播视频流链接的API接口，上传即可用
  </details>
  &emsp;

## 有问题可以提issue, 我会在这里持续添加更多直播平台的录制 欢迎Star
#### 

## 抖音 Docker 模式

该模式面向 NAS 和 Linux 服务器长期无人值守运行，入口为
`python -m app.douyin_daemon`。它只读取抖音 YAML 配置，不依赖终端、
TTY 或 `input()`；原有 `python main.py` 多平台源码入口保持不变。

### 1. 创建配置

复制 `config/douyin.example.yaml` 为 `config/douyin.yaml`，然后修改
`rooms`。支持直播间地址、主播主页地址和抖音短链接；解析后会按房间或
主播标识去重。

默认策略是 TS、每 1800 秒分段、直接封装 `-c copy`、不转 MP4、不删除
源文件。TS 在网络中断或容器停止时比 MP4 更容易保留可播放的尾部；
自动转 MP4 会额外占用 CPU、磁盘和后处理时间，因此 daemon 默认不做。

### 2. 配置 Cookie Secret

Cookie 的读取优先级为：

1. `DOUYIN_COOKIE_FILE`
2. `DOUYIN_COOKIE`
3. YAML 中的 `cookie.value`

推荐复制 `secrets/douyin_cookie.example.txt` 为宿主机私有文件，并设置：

```bash
DOUYIN_COOKIE_FILE_PATH=/绝对路径/douyin_cookie.txt docker compose up -d
```

不要把真实 Cookie 写入 YAML、镜像或 Git。日志只输出脱敏状态。

### 3. 启动、检查与停止

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=200
docker compose exec app python -m app.health check
docker compose stop
```

录制文件保存在宿主机 `downloads/`，健康状态保存在 Docker 命名卷
`douyin_state`。Linux/NAS 上应确保 `downloads/` 可由 UID 10001 写入。
代理通过 `proxy.url` 设置。健康检查关注
调度心跳、最近检测、目录可写性、剩余磁盘和 FFmpeg 连续崩溃，不会把
单个主播未开播判为故障。

收到 SIGTERM/SIGINT 后，daemon 会停止新检查和新录制，向全部 FFmpeg
发送 SIGINT 并等待文件尾写入；超时后才依次 terminate 和 kill。
Compose 为此保留 90 秒停止宽限期。

发布镜像支持 `linux/amd64` 和 `linux/arm64`。主分支发布 `edge`；
正式 `v*` Release 才发布版本标签和 `latest`。升级前应备份配置与下载
目录，拉取固定版本标签，重新创建容器并检查健康状态。
