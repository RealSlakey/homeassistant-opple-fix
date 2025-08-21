"""
Opple Light Integration (稳定性优化版)
- 减少少频繁的不可用状态显示
- 优化长设备响应等待时间
- 优化重试机制和状态判断逻辑
"""

import logging
import time
from datetime import timedelta
import voluptuous as vol
from pyoppleio.OppleLightDevice import OppleLightDevice

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_MAC,
)
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Opple Light"
BRIGHTNESS_MIN = 10
BRIGHTNESS_MAX = 255
COLOR_TEMP_MIN = 2700
COLOR_TEMP_MAX = 5700

# 优化更新频率（避免频繁请求导致设备响应慢）
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)
# 增加重试次数和间隔（给设备更多响应时间）
MAX_RETRIES = 3  # 从2次增加到3次
RETRY_DELAY = 1.0  # 从0.5秒延长到1秒（给设备足够处理时间）
# 连续失败多少次才标记为离线（容错：允许短暂波动）
CONSECUTIVE_FAILURE_THRESHOLD = 2


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_MAC): cv.string,
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config[CONF_NAME]
    host = config[CONF_HOST]
    mac = config[CONF_MAC]
    device = OppleLightDevice(host)
    async_add_entities([OppleLight(name, host, mac, device)], True)


class OppleLight(LightEntity):
    def __init__(self, name, host, mac, device):
        self._name = name
        self._host = host
        self._mac = mac
        self._device = device
        self._is_on = False
        self._brightness = 0
        self._color_temp_kelvin = COLOR_TEMP_MIN
        self._available = False  # 当前可用状态
        self._last_available = False  # 上一次可用状态（用于平滑过渡）
        self._consecutive_failures = 0  # 连续失败计数

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"opple_{self._mac.replace(':', '')}"

    @property
    def available(self):
        return self._available

    @property
    def is_on(self):
        return self._is_on

    @property
    def brightness(self):
        return self._brightness

    @property
    def color_mode(self):
        return ColorMode.COLOR_TEMP

    @property
    def supported_color_modes(self):
        return {ColorMode.COLOR_TEMP}

    @property
    def min_color_temp_kelvin(self):
        return COLOR_TEMP_MIN

    @property
    def max_color_temp_kelvin(self):
        return COLOR_TEMP_MAX

    @property
    def color_temp_kelvin(self):
        return self._color_temp_kelvin

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """优化状态更新逻辑：增加重试、容错少频繁标记离线"""
        try:
            # 重置临时变量
            current_available = False
            retry = 0

            # 多次重试获取状态（延长时间隔）
            while retry < MAX_RETRIES:
                try:
                    self._device.update()
                    current_available = self._device.is_online
                    if current_available:
                        # 成功获取状态，重置失败计数
                        self._consecutive_failures = 0
                        break
                    retry += 1
                    _LOGGER.debug(f"设备 {self._host} 重试获取状态({retry}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                except Exception as e:
                    retry += 1
                    _LOGGER.debug(f"设备 {self._host} 更新异常({retry}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)

            # 处理连续续失败：达到达到阈值值才标记为离线
            if not current_available:
                self._consecutive_failures += 1
                # 保留上一次可用状态，直到连续失败次数达标
                if self._consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                    self._available = False
                    _LOGGER.warning(f"设备 {self._host} 连续{self._consecutive_failures}次失败，标记为离线")
                else:
                    _LOGGER.debug(f"设备 {self._host} 暂时不可用（累计失败{self._consecutive_failures}次），保持上次状态")
                    # 沿用上次可用状态，避免频繁切换
                    self._available = self._last_available
                return

            # 成功获取状态，更新属性
            self._available = True
            self._last_available = True  # 记录当前可用状态
            self._is_on = self._device.power_on
            self._brightness = self._device.brightness
            self._color_temp_kelvin = self._device.color_temperature

            _LOGGER.debug(
                f"设备 {self._host} 状态: 在线={self._available}, "
                f"开关={self._is_on}, 亮度={self._brightness}, 色温={self._color_temp_kelvin}K"
            )

        except Exception as e:
            self._consecutive_failures += 1
            if self._consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                self._available = False
            _LOGGER.error(f"设备 {self._host} 更新失败: {str(e)}")

    async def async_turn_on(self, **kwargs):
        """优化控制后状态同步逻辑"""
        if not self._available:
            _LOGGER.warning(f"设备 {self._host} 离线，无法操作")
            return

        try:
            # 1. 开灯
            if not self._is_on:
                self._device.power_on = True
                _LOGGER.debug(f"设备 {self._host} 已开灯")

            # 2. 调节亮度
            if ATTR_BRIGHTNESS in kwargs:
                ha_bright = kwargs[ATTR_BRIGHTNESS]
                device_bright = int(ha_bright)
                device_bright = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, device_bright))
                self._device.brightness = device_bright
                _LOGGER.debug(f"设备 {self._host} 亮度设置为 {device_bright}")

            # 3. 调节色温
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
                kelvin = max(COLOR_TEMP_MIN, min(COLOR_TEMP_MAX, kelvin))
                self._device.color_temperature = kelvin
                _LOGGER.debug(f"设备 {self._host} 色温设置为 {kelvin}K")

            # 控制后延迟一小会（给设备处理时间，避免立即查询失败）
            await self.hass.async_add_executor_job(time.sleep, 0.3)
            await self.hass.async_add_executor_job(self._device.update)
            await self.async_update()

        except Exception as e:
            _LOGGER.error(f"设备 {self._host} 开灯/调节失败: {str(e)}")
            # 控制失败不立即标记离线（可能是临时错误）
            self._consecutive_failures += 1

    async def async_turn_off(self,** kwargs):
        """优化关灯后状态同步"""
        if not self._available:
            _LOGGER.warning(f"设备 {self._host} 离线，无法操作")
            return

        try:
            self._device.power_on = False
            _LOGGER.debug(f"设备 {self._host} 已关灯")
            # 延迟查询会再同步状态
            await self.hass.async_add_executor_job(time.sleep, 0.3)
            await self.hass.async_add_executor_job(self._device.update)
            await self.async_update()

        except Exception as e:
            _LOGGER.error(f"设备 {self._host} 关灯失败: {str(e)}")
            self._consecutive_failures += 1

    async def async_update(self):
        await self.hass.async_add_executor_job(self.update)
