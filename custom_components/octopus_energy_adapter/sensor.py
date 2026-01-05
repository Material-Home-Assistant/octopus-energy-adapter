import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import get_last_statistics

from .const import (
    DOMAIN,
    CONF_DATA_SENSOR,
    CONF_VALUE_SENSOR,
    CONF_PRICE_TYPE,
    CONF_FIXED_PRICE,
    CONF_PRICE_SENSOR,
    PRICE_TYPE_FIXED,
)
from .storage import load_data_sync, save_data_sync, has_date, add_day
from .statistics import push_statistics, push_bulk_statistics

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensors from a config entry."""
    config = entry.data
    async_add_entities([
        OctopusMonthlyEnergy(hass, config, entry.entry_id),
        OctopusMonthlyCost(hass, config, entry.entry_id)
    ], True)

class OctopusMonthlyEnergy(SensorEntity):
    """Dashboard sensor for cumulative energy."""

    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._attr_name = "Octopus Monthly Energy"
        self._attr_unique_id = f"octopus_monthly_energy_{entry_id}"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "kWh"
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        """Handle entity which is about to be added to Home Assistant."""
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        
        if data:
            sorted_dates = sorted(data.keys())
            self._state = data[sorted_dates[-1]]
            
            price = await self._get_current_price()
            self.hass.async_create_task(push_bulk_statistics(self.hass, data, price))
        else:
            self._state = 0

        data_src = self._config.get(CONF_DATA_SENSOR)
        value_src = self._config.get(CONF_VALUE_SENSOR)
        self.async_on_remove(
            async_track_state_change_event(self.hass, [data_src, value_src], self._async_on_dependency_update)
        )

    async def _async_on_dependency_update(self, event):
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        """Update the sensor state."""
        try:
            data_src = self._config.get(CONF_DATA_SENSOR)
            value_src = self._config.get(CONF_VALUE_SENSOR)
            
            date_state = self.hass.states.get(data_src)
            value_state = self.hass.states.get(value_src)

            if not date_state or not value_state or date_state.state in ["unknown", "unavailable"]:
                return

            reading_date = datetime.strptime(date_state.state, "%d/%m/%Y").strftime("%Y-%m-%d")
            daily_value = float(value_state.state)

            data = await self.hass.async_add_executor_job(load_data_sync, self.hass)

            if not has_date(data, reading_date):
                last_total = await self.get_last_total()
                new_total = round(last_total + daily_value, 3)

                add_day(data, reading_date, new_total)
                await self.hass.async_add_executor_job(save_data_sync, self.hass, data)

                price = await self._get_current_price()
                await push_statistics(self.hass, reading_date, new_total, price)
                
                self._state = new_total
        except Exception as e:
            _LOGGER.error("Error during update: %s", e)

    async def _get_current_price(self):
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        price_sensor = self._config.get(CONF_PRICE_SENSOR)
        if price_sensor:
            state = self.hass.states.get(price_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                return float(state.state)
        return 0.0

    async def get_last_total(self):
        stat_id = "sensor:octopus_energy_total"
        try:
            stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, stat_id, True, {"sum"}
            )
            if stats and stat_id in stats:
                return stats[stat_id][0]["sum"]
        except Exception:
            pass
        return self._state if self._state is not None else 0.0

class OctopusMonthlyCost(SensorEntity):
    """Dashboard sensor for cumulative cost."""
    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._attr_name = "Octopus Monthly Cost"
        self._attr_unique_id = f"octopus_monthly_cost_{entry_id}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "EUR"
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        stat_id = "sensor:octopus_energy_cost_total"
        try:
            stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, stat_id, True, {"sum"}
            )
            if stats and stat_id in stats:
                self._state = stats[stat_id][0]["sum"]
        except Exception:
            self._state = 0