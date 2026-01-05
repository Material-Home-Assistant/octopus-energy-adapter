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
    """Configura i sensori basandosi su un Config Entry."""
    config = entry.data
    # Devono esserci ENTRAMBI i sensori nella lista
    async_add_entities([
        OctopusEnergyTotal(hass, config, entry.entry_id),
        OctopusCostTotal(hass, config, entry.entry_id)
    ], True)

class OctopusEnergyTotal(SensorEntity):
    """Sensore che accumula l'energia e gestisce le statistiche di costo."""

    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._entry_id = entry_id
        
        # Attributi dell'entità
        self._attr_name = "Octopus Energy Total"
        self._attr_unique_id = f"octopus_energy_total_{entry_id}"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = "kWh"
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        """Inizializzazione all'avvio: carica storico e imposta i listener."""
        # 1. Carica i dati dal file JSON
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        
        if data:
            sorted_dates = sorted(data.keys())
            self._state = data[sorted_dates[-1]]
            
            # 2. Invia lo storico (Bulk Import) al database delle statistiche
            # Recuperiamo il prezzo attuale per lo storico (approssimativo)
            price = await self._get_current_price()
            self.hass.async_create_task(push_bulk_statistics(self.hass, data, price))
        else:
            self._state = 0

        # 3. Ascolta i cambiamenti dei sensori sorgente definiti nel Config Flow
        data_src = self._config.get(CONF_DATA_SENSOR)
        value_src = self._config.get(CONF_VALUE_SENSOR)
        
        self.async_on_remove(
            async_track_state_change_event(self.hass, [data_src, value_src], self._async_on_dependency_update)
        )
        
        _LOGGER.info("Octopus Adapter inizializzato con sensori: %s, %s", data_src, value_src)

    async def _async_on_dependency_update(self, event):
        """Callback eseguita quando i sensori Octopus cambiano valore."""
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        """Logica principale di aggiornamento dati e statistiche."""
        try:
            data_src = self._config.get(CONF_DATA_SENSOR)
            value_src = self._config.get(CONF_VALUE_SENSOR)
            
            date_state = self.hass.states.get(data_src)
            value_state = self.hass.states.get(value_src)

            if not date_state or not value_state or date_state.state in ["unknown", "unavailable"]:
                return

            # Formattiamo la data dal sensore (es. da 01/12/2025 a 2025-12-01)
            reading_date = datetime.strptime(date_state.state, "%d/%m/%Y").strftime("%Y-%m-%d")
            daily_value = float(value_state.state)

            # Carichiamo i dati attuali
            data = await self.hass.async_add_executor_job(load_data_sync, self.hass)

            if not has_date(data, reading_date):
                # Calcola il nuovo totale cumulativo
                last_total = await self.get_last_total()
                new_total = round(last_total + daily_value, 3)

                # Salva su file JSON
                add_day(data, reading_date, new_total)
                await self.hass.async_add_executor_job(save_data_sync, self.hass, data)

                # Recupera il prezzo e aggiorna le statistiche esterne (kWh e EUR)
                price = await self._get_current_price()
                await push_statistics(self.hass, reading_date, new_total, price)
                
                self._state = new_total
                _LOGGER.info("Aggiornato Octopus: %s kWh per il giorno %s", new_total, reading_date)

        except Exception as e:
            _LOGGER.error("Errore durante l'aggiornamento Octopus Adapter: %s", e)

    async def _get_current_price(self):
        """Recupera il prezzo in base alla configurazione del Config Flow."""
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        
        price_sensor = self._config.get(CONF_PRICE_SENSOR)
        if price_sensor:
            state = self.hass.states.get(price_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                return float(state.state)
        return 0.0

    async def get_last_total(self):
        """Recupera l'ultimo valore 'sum' dalle statistiche per evitare salti."""
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

class OctopusCostTotal(SensorEntity):
    """Nuovo sensore per tracciare il costo totale (EUR)."""

    def __init__(self, hass, config, entry_id):
        self.hass = hass
        self._config = config
        self._attr_name = "Octopus Energy Cost Total"
        self._attr_unique_id = f"octopus_energy_cost_total_{entry_id}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "EUR"
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        """Carica il valore iniziale al riavvio."""
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        """Recupera l'ultimo costo dalle statistiche."""
        stat_id = "sensor:octopus_energy_cost_total"
        try:
            stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, stat_id, True, {"sum"}
            )
            if stats and stat_id in stats:
                self._state = stats[stat_id][0]["sum"]
            else:
                # Se le statistiche sono vuote, proviamo a calcolarlo al volo dal valore attuale dell'energia
                energy_total = self.hass.states.get(f"sensor.octopus_energy_total_{self._config.get(DOMAIN)}")
                # Nota: Questo è un fallback, il metodo delle statistiche è più preciso
                self._state = self._state or 0
        except Exception:
            self._state = 0