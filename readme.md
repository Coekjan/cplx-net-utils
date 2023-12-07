# CPLX-NET-UTILS | 自动化 eNSP 网络设备配置

网络设备配置脚本，生成并导入华为 eNSP 模拟设备的各种网络参数设置。该脚本支持生成并应用设备的 IP 地址、路由配置、NAT 设置、OSPF 配置、MPLS 配置、BGP 配置以及 VPN 配置等。

## 安装

克隆本仓库。推荐 Python 版本为 `3.11`。

## 使用

首先，配置设备串口号，在设备关机的情况下，设备>设置>配置>串口号。

注意，运行脚本前需将要配置的设备启动，并打开命令行。

其次，导入设置，配置脚本在 `*.sh` 里面。

```bash
python nnet.py asx.sh
```

最终，`cfgs`目录下生成了具体的配置文件，`outs`目录下生成了设备的输出。

## 配置

在 `nnet.py` 里面：

|名称|内容|
|-|-|
|`SKIP_SUBMIT`|是否提交到设备。|
|`SAVE_ALL`|值为 1 时，在设置路由器时会尝试保存配置信息。当值为 2 时，会清除之前的配置并保存新的配置。如果值为 0，则不会保存任何配置信息。|
|`DELAY`|第一次导入设置可以不加延迟，之后需要覆盖之前设备配置的时候需要启用延迟。|
|`mypre`| IP 前缀，替换脚本里的`@`。|
|`dev_open_mode`| 设备打开模式，写入或追加。|

`*.sh` 请看 `as1.sh` 的注释内容。

## 原理

脚本并非直接将配置写入 eNSP，而是利用 eNSP 模拟设备具有的串口号，通过 Python 的 Telnet 登录到 `127.0.0.1:port`，最后将网络配置命令以文本形式发送给这些设备，模拟了在实际设备上进行配置的过程。

## 感谢

本项目源于 @karin0 本科时期的脚本。

感谢谷云超、张力军等老师的帮助。