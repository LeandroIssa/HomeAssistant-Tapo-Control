from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .tapo.entities import TapoSelectEntity
from .utils import check_and_create


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    LOGGER.debug("Setting up selects")
    entry = hass.data[DOMAIN][config_entry.entry_id]

    selects = []
    selects.append(TapoNightVisionSelect(entry, hass, config_entry))
    selects.append(TapoAutomaticAlarmModeSelect(entry, hass, config_entry))
    selects.append(TapoLightFrequencySelect(entry, hass, config_entry))
    selects.append(
        await check_and_create(
            entry, hass, TapoMotionDetectionSelect, "getAutoTrackTarget", config_entry
        )
    )
    selects.append(
        await check_and_create(
            entry, hass, TapoMoveToPresetSelect, "getPresets", config_entry
        )
    )

    async_add_entities(selects)


class TapoNightVisionSelect(TapoSelectEntity):
    def __init__(self, entry: dict, hass: HomeAssistant, config_entry):
        self._attr_options = ["auto", "on", "off"]
        self._attr_current_option = None
        TapoSelectEntity.__init__(
            self,
            "Night Vision",
            entry,
            hass,
            config_entry,
            "mdi:theme-light-dark",
            "night_vision",
        )

    def updateTapo(self, camData):
        if not camData:
            self._attr_state = "unavailable"
        else:
            self._attr_current_option = camData["day_night_mode"]

    async def async_select_option(self, option: str) -> None:
        await self._hass.async_add_executor_job(
            self._controller.setDayNightMode, option
        )


class TapoLightFrequencySelect(TapoSelectEntity):
    def __init__(self, entry: dict, hass: HomeAssistant, config_entry):
        self._attr_options = ["auto", "50", "60"]
        self._attr_current_option = None
        TapoSelectEntity.__init__(
            self, "Light Frequency", entry, hass, config_entry, "mdi:sine-wave"
        )

    async def async_update(self) -> None:
        self._attr_current_option = await self._hass.async_add_executor_job(
            self._controller.getLightFrequencyMode
        )

    def updateTapo(self, camData):
        if not camData:
            self._attr_state = "unavailable"
        else:
            self._attr_current_option = camData["light_frequency_mode"]

    async def async_select_option(self, option: str) -> None:
        await self._hass.async_add_executor_job(
            self._controller.setLightFrequencyMode, option
        )


class TapoAutomaticAlarmModeSelect(TapoSelectEntity):
    def __init__(self, entry: dict, hass: HomeAssistant, config_entry):
        self._attr_options = ["both", "light", "sound", "off"]
        self._attr_current_option = None
        TapoSelectEntity.__init__(
            self,
            "Automatic Alarm",
            entry,
            hass,
            config_entry,
            "mdi:alarm-check",
            "alarm",
        )

    def updateTapo(self, camData):
        if not camData:
            self._attr_state = "unavailable"
        else:
            if camData["alarm"] == "off":
                self._attr_current_option = "off"
            else:
                light = "light" in camData["alarm_mode"]
                sound = "sound" in camData["alarm_mode"]
                if light and sound:
                    self._attr_current_option = "both"
                elif light and not sound:
                    self._attr_current_option = "light"
                else:
                    self._attr_current_option = "sound"

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(
            self._controller.setAlarm,
            option != "off",
            option == "off" or option in ["both", "sound"],
            option == "off" or option in ["both", "light"],
        )


class TapoMotionDetectionSelect(TapoSelectEntity):
    def __init__(self, entry: dict, hass: HomeAssistant, config_entry):
        self._attr_options = ["high", "normal", "low", "off"]
        self._attr_current_option = None
        TapoSelectEntity.__init__(
            self,
            "Motion Detection",
            entry,
            hass,
            config_entry,
            "mdi:motion-sensor",
            "motion_detection",
        )

    def updateTapo(self, camData):
        if not camData:
            self._attr_state = "unavailable"
        else:
            if camData["motion_detection_enabled"] == "off":
                self._attr_current_option = "off"
            else:
                self._attr_current_option = camData["motion_detection_sensitivity"]

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(
            self._controller.setMotionDetection,
            option != "off",
            option if option != "off" else False,
        )
        await self._coordinator.async_request_refresh()


class TapoMoveToPresetSelect(TapoSelectEntity):
    def __init__(self, entry: dict, hass: HomeAssistant, config_entry):
        self._presets = {}
        self._attr_options = []
        self._attr_current_option = None
        TapoSelectEntity.__init__(
            self, "Move to Preset", entry, hass, config_entry, "mdi:arrow-decision"
        )

    def updateTapo(self, camData):
        if not camData:
            self._attr_state = "unavailable"
        else:
            self._attr_state = "idle"
            self._presets = camData["presets"]
            self._attr_options = list(camData["presets"].values())
            self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        foundKey = False
        for key, value in self._presets.items():
            if value == option:
                foundKey = key
                break
        if foundKey:
            await self.hass.async_add_executor_job(self._controller.setPreset, foundKey)
            self._attr_current_option = None
        else:
            LOGGER.error(f"Preset {option} does not exist.")