"""
The chinese calendar information comes from Juhe.
"""
import asyncio
import async_timeout
import aiohttp
import logging
import json
from datetime import timedelta
import voluptuous as vol

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)


CONF_ATTRIBUTION = "Today's lunar calendar provided by Juhe"
CONF_KEY = 'key'

DEFAULT_NAME = 'calendar'
ICON = 'mdi:yin-yang'


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_KEY):cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the LunarCalendar sensor."""

    key = config.get(CONF_KEY)

    data = JuheLunarCalendarData(hass, key)
    yield from data.async_update(dt_util.now())
    async_track_time_change( hass, data.async_update, hour=[0], minute=[0], second=[1] )

    dev = []
    dev.append(JuheLunarCalendarSensor(data))
    async_add_devices(dev, True)


class JuheLunarCalendarSensor(Entity):
    """Representation of a Juhe LunarCalendar sensor."""

    def __init__(self, data):
        """Initialize the sensor."""
        self._data = data
        self._name = DEFAULT_NAME

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name


    @property
    def state(self):
        """Return the state of the sensor."""
        return self._data.lunar

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self._data is not None:
            return {
                "公历年": self._data.year,
                "公历月": self._data.month,
                "公历日": self._data.day,
                "数字农历年": self._data.lunarYear,
                "数字农历月": self._data.lunarMonth,
                "数字农历日": self._data.lunarDay,
                "中文农历年": self._data.cnyear,
                "中文农历月": self._data.cnmonth,
                "中文农历日": self._data.cnday,
                "年": self._data.hyear,
                "甲子年": self._data.cyclicalYear,
                "甲子月": self._data.cyclicalMonth,
                "甲子日": self._data.cyclicalDay,
                "宜": self._data.suit,
                "禁": self._data.taboo,
                "生肖": self._data.animal,
                "星期": self._data.week,
                "节日": self._data.festivalList,
                "节气": self._data.jieqi,
                "农历月天数": self._data.maxDayInMonth,
                "闰月": self._data.leap,
                "大月": self._data.bigMonth,
                "农历年": self._data.lunarYearString
            }

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON
    
    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and updates the states."""



class JuheLunarCalendarData(object):
    """Get data from Juhe LunarCalendar imformation."""

    def __init__(self, hass, key):
        """Initialize the data object."""
        self.year = None
        self.month = None
        self.day=None
        self.lunarYear=None
        self.lunarMonth=None
        self.lunarDay=None
        self.cnyear=None
        self.cnmonth=None
        self.cnday=None
        self.hyear=None
        self.cyclicalYear=None
        self.cyclicalMonth=None
        self.cyclicalDay=None
        self.suit=None
        self.taboo=None
        self.animal=None
        self.week=None
        self.festivalList=None
        self.jieqi=None
        self.maxDayInMonth=None
        self.leap=None
        self.bigMonth=None
        self.lunarYearString=None
        
        self.hass = hass

        #self.url = "http://v.juhe.cn/calendar/day"
        self.url = "https://www.sojson.com/open/api/lunar/json.shtml"
        #self.key = key


    @asyncio.coroutine
    def async_update(self, now):
        """Get the latest data and updates the states."""

        date = now.strftime("%Y-%m-%d")
        params = {
            #"key": self.key,
            "date": date,
            }

        try:
            session = async_get_clientsession(self.hass)
            with async_timeout.timeout(15, loop=self.hass.loop):
                response = yield from session.post( self.url, data=params )

        except(asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Error while accessing: %s", self.url)
            return

        if response.status != 200:
            _LOGGER.error("Error while accessing: %s, status=%d", self.url, response.status)
            return

        result = yield from response.json()

        if result is None:
            _LOGGER.error("Request api Error: %s", self.url)
            return
        elif (result["status"] != 200):
            _LOGGER.error("Error API return, errorcode=%s, reson=%s",
                          result["status"],
                          result["message"],
                          )
            return
          
        self.year = result["result"]["year"]
        self.month = result["result"]["month"]
        self.day = result["result"]["day"]
        self.lunarYear = result["result"]["lunarYear"]
        self.lunarMonth = result["result"]["lunarMonth"]
        self.lunarDay = result["result"]["lunarDay"]
        self.cnyear = result["result"]["cnyear"]
        self.cnmonth = result["result"]["cnmonth"]
        self.cnday = result["result"]["cnday"]
        self.hyear=result["result"]["hyear"]
        self.cyclicalYear=result["result"]["cyclicalYear"]
        self.cyclicalMonth=result["result"]["cyclicalMonth"]
        self.cyclicalDay=result["result"]["cyclicalDay"]
        self.suit=result["result"]["suit"]
        self.taboo=result["result"]["taboo"]
        self.animal=result["result"]["animal"]
        self.week=result["result"]["week"]
        self.festivalList=result["result"]["festivalList"]
        self.jieqi=result["result"]["jieqi"]
        self.maxDayInMonth=result["result"]["maxDayInMonth"]
        self.leap=result["result"]["leap"]
        self.bigMonth=result["result"]["bigMonth"]
        self.lunarYearString=result["result"]["lunarYearString"]