# 说明 2025-8-21
本Repo通过KIMI修改+人工修改
以试图修复以下问题：
- 减少频繁的不可用状态显示
- 优化长设备响应等待时间
- 优化重试机制和状态判断逻辑
- configuration.yaml中手动配置mac地址，以便生成unique id
  
本人测试中，原Repo存在如果配置两盏opple灯，会偶发性出现两盏灯混乱的问题，在HA的issues中也有人提到过，但官方并未解决，使用本fork后，*实测大大减少了不可用状态、两盏灯也暂无出现错乱的情况*，本fork需安装依赖*pyoppleio*

docker中查看pyoppleio的版本命令：
```shell
docker exec homeassistant pip show pyoppleio
```
查看是否输出类似以下内容：
```shell
root@iStoreOS:~# docker exec homeassistant pip show pyoppleio
Name: pyoppleio
Version: 1.0.5
Summary: Python library for interfacing with opple mobile control light
Home-page: https://github.com/jedmeng/python-oppleio
Author: jedmeng
Author-email: jedm@jedm.cn
License: MIT
Location: /usr/local/lib/python3.13/site-packages
Requires: crc16
Required-by: 
```

docker中安装pyoppleio的版本命令：
```shell
docker exec homeassistant pip install pyoppleio crc16
```

configuration.yaml示例
```yaml
light:
  - platform: opple_fix         # 使用我们的自定义集成
    name: 玄关吊灯
    host: 192.168.5.101
    mac: 68:79:c4:00:12:34
  - platform: opple_fix
    name: 客厅吊灯
    host: 192.168.5.51
    mac: 68:79:c4:00:56:78
```

若还是出现不可用或两灯错乱的情况，尝试删除旧实体，在路由中更改并固定灯具IP

## 已知问题
- 会导致homebridge中，无法该集成的灯具显示无响应，期待大佬解决

# 原README.md：
***************
WARNING: THIS REPOSITORY IS DEPRECATED
====================================
This component has been merged into [Home Assistant](https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/light/opple.py) and this repository is no longer being maintained.
***************

[Home Assistant](https://www.home-assistant.io/) component of [opple](http://www.opple.com/) devices

# Supported Devices

All opple light with WIFI support (mobile control)

e.g.
![demo](https://img.alicdn.com/imgextra/i2/138006397/TB2mgp_XSOI.eBjSspmXXatOVXa_!!138006397.jpg)
![demo2](https://img.alicdn.com/imgextra/i3/138006397/TB2etN_XHOJ.eBjy1XaXXbNupXa_!!138006397.jpg)

# Install
copy the `custom_components` to your home-assistant config directory.

# config
Add the following to your configuration.yaml file:
```yaml
light:
  - platform: opple
    name: light_1
    host: 192.168.0.101
  - platform: opple
    name: light_2
    host: 192.168.0.102
```

CONFIGURATION VARIABLES:

- name
  (string)(Optional)The display name of the light

- host
  (string)(Required)The host/IP address of the light.
