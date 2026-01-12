import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

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

# Segnali per la comunicazione tra sensori
SIGNAL_ENERGY_UPDATE = f"{DOMAIN}_energy_updated"
SIGNAL_PRICE_UPDATE = f"{DOMAIN}_price_updated"

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensors from a config entry."""
    config = entry.data
    
    energy_sensor = OctopusMonthlyEnergy(hass, config, entry.entry_id)
    cost_sensor = OctopusMonthlyCost(hass, config, entry_id=entry.entry_id)
    price_sensor = OctopusCurrentPrice(hass, config, entry.entry_id)
    
    async_add_entities([energy_sensor, cost_sensor, price_sensor], True)

class OctopusCurrentPrice(SensorEntity):
    """Sensore che espone il prezzo attuale applicato per kWh."""

    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._attr_name = "Octopus Current Price"
        self._attr_unique_id = f"octopus_current_price_{entry_id}"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "EUR/kWh"
        self._state = 0.0

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        if self._config.get(CONF_PRICE_TYPE) != PRICE_TYPE_FIXED:
            p_src = self._config.get(CONF_PRICE_SENSOR)
            if p_src:
                self.async_on_remove(
                    async_track_state_change_event(self.hass, [p_src], self._async_on_price_change)
                )
        await self.async_update()

    async def _async_on_price_change(self, event):
        await self.async_update()
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_PRICE_UPDATE)

    async def async_update(self):
        self._state = await self._get_current_price()

    async def _get_current_price(self):
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        p_src = self._config.get(CONF_PRICE_SENSOR)
        if p_src:
            st = self.hass.states.get(p_src)
            if st and st.state not in ["unknown", "unavailable"]:
                return float(st.state)
        return 0.0

class OctopusMonthlyEnergy(SensorEntity):
    """Sensore Energia: Legge il JSON e calcola il mensile."""

    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._attr_name = "Octopus Monthly Energy"
        self._attr_unique_id = f"octopus_monthly_energy_{entry_id}"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "kWh"
        self._state = 0.0

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        if data:
            self._state = self._calculate_monthly_value(data)
            price = await self._get_current_price()
            self.hass.async_create_task(push_bulk_statistics(self.hass, data, price))
            async_dispatcher_send(self.hass, SIGNAL_ENERGY_UPDATE, self._state)

        data_src = self._config.get(CONF_DATA_SENSOR)
        value_src = self._config.get(CONF_VALUE_SENSOR)
        self.async_on_remove(
            async_track_state_change_event(self.hass, [data_src, value_src], self._async_on_dependency_update)
        )

    def _calculate_monthly_value(self, data):
        if not data: return 0.0
        sorted_dates = sorted(data.keys())
        last_total = data[sorted_dates[-1]]
        first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        base_value = 0.0
        for d in reversed(sorted_dates):
            if d < first_of_month:
                base_value = data[d]
                break
        return round(last_total - base_value, 3)

    async def _async_on_dependency_update(self, event):
        await self.async_update()
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_ENERGY_UPDATE, self._state)

    async def async_update(self):
        try:
            d_st = self.hass.states.get(self._config.get(CONF_DATA_SENSOR))
            v_st = self.hass.states.get(self._config.get(CONF_VALUE_SENSOR))
            if not d_st or not v_st or d_st.state in ["unknown", "unavailable"]: return

            reading_date = datetime.strptime(d_st.state, "%d/%m/%Y").strftime("%Y-%m-%d")
            daily_val = float(v_st.state)
            data = await self.hass.async_add_executor_job(load_data_sync, self.hass)

            if not has_date(data, reading_date):
                last_cum = data[sorted(data.keys())[-1]] if data else 0.0
                new_cum = round(last_cum + daily_val, 3)
                add_day(data, reading_date, new_cum)
                await self.hass.async_add_executor_job(save_data_sync, self.hass, data)

                price = await self._get_current_price()
                await push_statistics(self.hass, reading_date, new_cum, price)
                self._state = self._calculate_monthly_value(data)
        except Exception as e:
            _LOGGER.error("Errore Energia: %s", e)

    async def _get_current_price(self):
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        p_src = self._config.get(CONF_PRICE_SENSOR)
        if p_src:
            st = self.hass.states.get(p_src)
            if st and st.state in ["unknown", "unavailable"] == False:
                return float(st.state)
        return 0.0

class OctopusMonthlyCost(SensorEntity):
    """Sensore Costo: Include il prezzo corrente negli attributi."""

    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._attr_name = "Octopus Monthly Cost"
        self._attr_unique_id = f"octopus_monthly_cost_{entry_id}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "EUR"
        self._state = 0.0
        self._last_energy = 0.0
        self._current_price = 0.0

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        """Aggiunge attributi extra per visibilità in dashboard."""
        return {
            "current_price": self._current_price,
            "price_unit": "EUR/kWh"
        }

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_ENERGY_UPDATE, self._update_from_energy))
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_PRICE_UPDATE, self._update_from_price))
        
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        if data:
            self._last_energy = self._calculate_current_monthly_energy(data)
            await self._refresh_cost()

    def _calculate_current_monthly_energy(self, data):
        sorted_dates = sorted(data.keys())
        last_total = data[sorted_dates[-1]]
        first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        base = 0.0
        for d in reversed(sorted_dates):
            if d < first_of_month:
                base = data[d]
                break
        return round(last_total - base, 3)

    async def _update_from_energy(self, energy_val):
        self._last_energy = energy_val
        await self._refresh_cost()

    async def _update_from_price(self):
        await self._refresh_cost()

    async def _refresh_cost(self):
        self._current_price = await self._get_current_price()
        self._state = round(self._last_energy * self._current_price, 2)
        self.async_write_ha_state()

    async def _get_current_price(self):
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        p_src = self._config.get(CONF_PRICE_SENSOR)
        if p_src:
            st = self.hass.states.get(p_src)
            if st and st.state not in ["unknown", "unavailable"]:
                return float(st.state)
        return 0.0