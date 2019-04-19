'''
版本：v0.03
修改内容：
1.直接从网上获取电台名称（当前总数量达到880个，呵呵），匹配你在收音机里的收藏电台；
2.自动从网上获取更新电台图标，电台当前节目名；
3.将主动状态查询周期由默认的10秒更改为60秒(时间长短只会影响电台图符和节目名的获取) -:)（因为有了
    这插件，实在没必要在app里操作收音机了，除了通过app添加收藏电台。）；
4.解决了当整点或整半点节目名称切换出现空白时的出错；

版本：v0.02
修改内容：
1.去除与收音机无关的信息（警戒状态、空调模式、插座功率、插座状态）；
2.增加turn on / turn off功能，便于Google Home控制（可以调整音量）；
3.解决点击播放、换曲后不能及时更新的问题（现在需要2秒暂缓）；
4.修正上一电台在最后电台切换时的错误；
5.当电台名称在组件里有记录的播放时，只显示名称，不显示代码；
6.添加了自动生成当前收音机已收藏的电台清单，并通过选择直接播放；

使用说明：
1.适用于HA0.88之后的版本，之前的版本需修改文件名和所在目录名；
2.只在lumi.gateway.v3、lumi.acpartner.v3两款网关上测试过；
3.配置文件里添加：
media_player:
  - platform: mi_ac_partner
    name: 
    host: 
    token: 

4.将本文件media_player.py放到：../custom_components/mi_ac_partner/目录下。
5.重启Home Assistant。

von(vaughan.zeng@gmail.com)
'''
import logging
from datetime import timedelta
import voluptuous as vol
import time
import urllib.request

from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TOKEN,
    STATE_PAUSED, STATE_PLAYING, STATE_OFF)
from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC, MEDIA_TYPE_PLAYLIST, SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_PLAY_MEDIA, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SELECT_SOURCE, SUPPORT_VOLUME_SET, SUPPORT_TURN_OFF, SUPPORT_TURN_ON)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Xiaomi AC Partner'
ICON = 'mdi:radio'

SCAN_INTERVAL = timedelta(seconds=60)

SUPPORT_XIAOMIACPARTNER = SUPPORT_VOLUME_SET | SUPPORT_PAUSE | SUPPORT_PLAY |\
    SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK | SUPPORT_SELECT_SOURCE | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
}, extra=vol.ALLOW_EXTRA)

category_id = [1,2,3,4,5,6,7,8,10,11,12,13,14,15]

def setup_platform(hass, config, add_devices, discovery_info = None):
    from miio import Device, DeviceException

    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    token = config.get(CONF_TOKEN)

    _LOGGER.info('米家空调伴侣（网关）%s初始化......',name)

    midevice = Device(host, token)
    acPartner = XiaomiacPartner(midevice, name)

    add_devices([acPartner], True)

class XiaomiacPartner(MediaPlayerDevice):
    """Representation of a Spotify controller."""
    def __init__(self, midevice, name):
        """Initialize."""
        self._midevice = midevice
        self._name = name
        self._state = None
        self._current_station_name = None
        self._volume = None
        self._image_url = None
        self._programname = None
        self._current_station_id = None
        self._current_selected_station = None
        self._source_list = []

        self._get_prop = False
        self._virtual_off = False

    def update(self):
        """Update state and attributes."""
        _LOGGER.info('更新米家空调伴侣（网关）%s状态数据......开始......',self._name)

        stations_total = []
        for id in category_id:
            url = 'http://live.ximalaya.com/live-web/v2/radio/category?categoryId={}&pageNum=1&pageSize=200'
            url = url.format(id)
            response = urllib.request.urlopen(url).read()
            list1 = (eval(response))['data']['data']
            stations_total = stations_total +list1

        self._stations_total = stations_total
        _LOGGER.info('网络电台总数量：%s',len(self._stations_total))

        if self._get_prop:
            time.sleep(2)
            self._get_prop = False

        # Availabel Radio favorites stations list
        channels = self._midevice.send("get_channels", {"start": 0})
        chs = channels["chs"]
        self._favorites_channels = chs
        stations = []
        a = len(self._favorites_channels)
        x = 0
        while x <= a-1:
            b = self._favorites_channels[x]['id']
            station_name_dict = self.stations_index(b)
            if station_name_dict == None:
                name = str(self._favorites_channels[x]['id']) + ' ' + '电台名不在总表中，太神奇了！'
                _LOGGER.warning('空调伴侣（网关）中收藏的电台（代码：%s）不在自动生成的电台总表中，太神奇了，应该是列表网站在更新，再等几个更新周期看看。',self._favorites_channels[x]['id'])
            else:
                name = str(self._favorites_channels[x]['id']) + ' ' + station_name_dict['name']
            x +=1
            stations.append(name)
        self._source_list = stations

        # Current station id and name
        status = self._midevice.send("get_prop_fm", [])
        self._current_station_id = status["current_program"]
        for i in range(len(self._source_list)):
            if str(self._current_station_id) in self._source_list[i]:
                current_name = self._source_list[i].split(' ',1)[1]
                current_source = self._source_list[i]
                break

        self._current_station_name = current_name
        self._current_selected_station = current_source

        # Current station image url and program name
        current_station_dict = self.stations_index(self._current_station_id)
        if current_station_dict == None:
            self._image_url = None
            self._programname = None
        else:
            self._image_url = current_station_dict['coverLarge']
            if current_station_dict['programName'] == None:
                self._programname = ' '
            else:
                self._programname = current_station_dict['programName']

        # Current volume
        self._volume = int(status['current_volume']) / 100

        # Current radio state
        if status['current_status'] == 'run':
            self._state = STATE_PLAYING
        else:
            self._state = STATE_PAUSED

        if self._virtual_off:
            self._state = STATE_OFF

        _LOGGER.info('更新米家空调伴侣（网关）%s状态数据......结束......收音机%s',self._name, self._state)

    def stations_index(self, key):
        for idx, val in enumerate(self._stations_total):
            if val['id'] == key:
                station_name_dict = self._stations_total[idx]
                return station_name_dict

    def set_volume_level(self, volume):
        """Set the volume level."""
        self._midevice.send('volume_ctrl_fm',[str(volume * 100)])
        self._get_prop = True
        _LOGGER.info('按下调整音量按键VVVVVVVVVVVVV')

    def media_next_track(self):
        """Skip to next track."""
        self.radio_index('next')
        self._get_prop = True
        _LOGGER.info('按下下一个电台按键NNNNNNNNNNN')

    def media_previous_track(self):
        """Skip to previous track."""
        self.radio_index('previous')
        self._get_prop = True
        _LOGGER.info('按下上一个电台按键PPPPPPPPPPP')

    def radio_index(self, key):
        if len(self._favorites_channels) < 1:
            _LOGGER.warning('请先在米家app端里对相应的空调伴侣（网关）收音机收藏至少一个电台！')
            return False
        for idx, val in enumerate(self._favorites_channels):
            if val["id"] == self._current_station_id:
                current_index = idx
                break
 
        if key == 'next':
            if current_index >= len(self._favorites_channels) - 1:
                current_index = 0
            else:
                current_index += 1
        elif key == 'previous':
            if current_index == 0:
                current_index = len(self._favorites_channels) - 1
            else:
                current_index -= 1

        channel = self._favorites_channels[current_index]
        self._midevice.send("play_specify_fm", {'id': channel["id"], 'type': 0})

    def media_play(self):
        """Start or resume playback."""
        self._midevice.send('play_fm',["on"])
        self._get_prop = True
        _LOGGER.info('按下播放键XXXXXXXX  %s',self._state)

    def media_pause(self):
        """Pause playback."""
        self._midevice.send('play_fm',["off"])
        _LOGGER.info('按下暂停键XXXXXXXX  %s',self._state)

    def turn_on(self):
        """Turn the media player on."""
        self._midevice.send('play_fm',["on"])
        self._virtual_off = False
        self._get_prop = True
        _LOGGER.info('打开电源')

    def turn_off(self):
        """Turn the media player off."""
        self._midevice.send('play_fm',["off"])
        self._virtual_off = True
        _LOGGER.info('关闭电源')

    def select_source(self, source):
        """Select playback device."""
        for i in range(len(self._source_list)):
            if source in self._source_list[i]:
                code = self._source_list[i].split(' ',1)[0]
                break

        self._midevice.send("play_specify_fm", {'id': int(code), 'type': 0})
        self._get_prop = True

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def icon(self):
        """Return the icon."""
        return ICON

    @property
    def state(self):
        """Return the playback state."""
        return self._state

    @property
    def volume_level(self):
        """Return the device volume."""
        return self._volume

    @property
    def source_list(self):
        """Return a list of source devices."""
        if self._source_list:
            return list(self._source_list)

    @property
    def source(self):
        """Return the current playback device."""
        return self._current_selected_station

    @property
    def media_artist(self):
        """Return the artist of current playing media (Music track only)."""
        return self._current_station_name

    @property
    def media_title(self):
        """Return the media title."""
        return self._programname

    @property
    def media_track(self):
        """Return the track number of current media (Music track only)."""
        return self._current_station_id

    @property
    def media_image_url(self):
        """Return the image url of current playing media."""
        return self._image_url

    @property
    def app_name(self):
        """Return the current running application."""
        return self._midevice.send('miIO.info',[])['model']

    @property
    def supported_features(self):
        """Return the media player features that are supported."""
        return SUPPORT_XIAOMIACPARTNER

    @property
    def media_content_type(self):
        """Return the media type."""
        return MEDIA_TYPE_MUSIC

