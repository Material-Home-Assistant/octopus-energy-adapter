import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.event import async_track_state_change_event

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
    """Sensor that calculates monthly consumption internally based on JSON."""

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
        """Inizializzazione e calcolo del valore mensile al riavvio."""
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        
        if data:
            self._state = self._calculate_monthly_value(data)
            price = await self._get_current_price()
            self.hass.async_create_task(push_bulk_statistics(self.hass, data, price))
        else:
            self._state = 0

        data_src = self._config.get(CONF_DATA_SENSOR)
        value_src = self._config.get(CONF_VALUE_SENSOR)
        self.async_on_remove(
            async_track_state_change_event(self.hass, [data_src, value_src], self._async_on_dependency_update)
        )

    def _calculate_monthly_value(self, data):
        """Calcola il consumo relativo al mese solare corrente."""
        if not data:
            return 0
        
        sorted_dates = sorted(data.keys())
        last_total = data[sorted_dates[-1]]
        
        # Primo giorno del mese corrente (es. 2026-01-01)
        first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        # Cerca l'ultimo valore disponibile prima di questo mese
        base_value = 0
        for d in reversed(sorted_dates):
            if d < first_of_month:
                base_value = data[d]
                break
        
        return round(last_total - base_value, 3)

    async def _async_on_dependency_update(self, event):
        """Callback per l'aggiornamento quando i sensori Octopus cambiano."""
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        """Aggiornamento dati: il JSON è l'unica fonte di verità."""
        try:
            data_src = self._config.get(CONF_DATA_SENSOR)
            value_src = self._config.get(CONF_VALUE_SENSOR)
            
            date_state = self.hass.states.get(data_src)
            value_state = self.hass.states.get(value_src)

            if not date_state or not value_state or date_state.state in ["unknown", "unavailable"]:
                return

            reading_date = datetime.strptime(date_state.state, "%d/%m/%Y").strftime("%Y-%m-%d")
            daily_value = float(value_state.state)

            # Carica il file JSON
            data = await self.hass.async_add_executor_job(load_data_sync, self.hass)

            if not has_date(data, reading_date):
                # Recupera l'ultimo totale direttamente dal JSON invece che dal database
                last_cum_total = 0
                if data:
                    sorted_dates = sorted(data.keys())
                    last_cum_total = data[sorted_dates[-1]]
                
                # Calcola il nuovo totale cumulativo
                new_cum_total = round(last_cum_total + daily_value, 3)

                # Salva nel file JSON
                add_day(data, reading_date, new_cum_total)
                await self.hass.async_add_executor_job(save_data_sync, self.hass, data)

                # Invia alle statistiche esterne (:)
                price = await self._get_current_price()
                await push_statistics(self.hass, reading_date, new_cum_total, price)
                
                # Ricalcola lo stato del sensore mensile per la dashboard
                self._state = self._calculate_monthly_value(data)
                _LOGGER.info("Octopus: Added %s kWh. New cumulative: %s", daily_value, new_cum_total)

        except Exception as e:
            _LOGGER.error("Error updating Octopus Monthly Energy: %s", e)

    async def _get_current_price(self):
        """Recupera il prezzo configurato."""
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        price_sensor = self._config.get(CONF_PRICE_SENSOR)
        if price_sensor:
            state = self.hass.states.get(price_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                return float(state.state)
        return 0.0

class OctopusMonthlyCost(SensorEntity):
    """Sensor that calculates monthly cost based on the monthly energy sensor."""

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
        """Moltiplica il consumo mensile attuale per il prezzo corrente."""
        try:
            energy_val = 0
            # Ottiene lo stato del sensore energia mensile appena calcolato
            energy_entity_id = f"sensor.octopus_monthly_energy_{self._config.get(DOMAIN)}"
            energy_state = self.hass.states.get(energy_entity_id)
            
            if energy_state and energy_state.state not in ["unknown", "unavailable"]:
                energy_val = float(energy_state.state)
                price = await self._get_current_price()
                self._state = round(energy_val * price, 2)
        except Exception:
            self._state = 0

    async def _get_current_price(self):
        """Recupera il prezzo configurato (duplicato per indipendenza)."""
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        price_sensor = self._config.get(CONF_PRICE_SENSOR)
        if price_sensor:
            state = self.hass.states.get(price_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                return float(state.state)
        return 0.0