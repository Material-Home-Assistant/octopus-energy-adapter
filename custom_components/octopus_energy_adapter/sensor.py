"""
Questo modulo gestisce la creazione e l'aggiornamento dei sensori per l'integrazione Octopus Energy Adapter.
Vengono creati tre sensori principali: Prezzo Attuale, Energia Mensile e Costo Mensile.
"""

import logging
from datetime import datetime

# Import dei componenti core di Home Assistant per la gestione dei sensori
from homeassistant.components.sensor import (
    SensorDeviceClass,  # Definisce il tipo di sensore (energia, monetario, ecc.)
    SensorEntity,       # La classe base per tutte le entità sensore
    SensorStateClass,   # Definisce come viene trattato il dato (misurazione, totale, ecc.)
)

# Helper per tracciare i cambiamenti di stato di altre entità e gestire segnali interni
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

# Costanti locali dell'integrazione
from .const import (
    DOMAIN,
    CONF_DATA_SENSOR,
    CONF_VALUE_SENSOR,
    CONF_PRICE_TYPE,
    CONF_FIXED_PRICE,
    CONF_PRICE_SENSOR,
    PRICE_TYPE_FIXED,
)

# Metodi per la gestione della persistenza dati e statistiche storiche
from .storage import load_data_sync, save_data_sync, has_date, add_day
from .statistics import push_statistics, push_bulk_statistics

_LOGGER = logging.getLogger(__name__)

# Segnali del dispatcher: servono per far comunicare i sensori tra loro senza dipendenze dirette.
# Quando il sensore Energia si aggiorna, avvisa il sensore Costo di ricalcolare.
SIGNAL_ENERGY_UPDATE = f"{DOMAIN}_energy_updated"
SIGNAL_PRICE_UPDATE = f"{DOMAIN}_price_updated"

async def async_setup_entry(hass, entry, async_add_entities):
    """
    Punto di ingresso per la configurazione dei sensori tramite Config Entry.
    Viene chiamato da Home Assistant durante il caricamento dell'integrazione.
    """
    config = entry.data
    
    # Inizializziamo le tre entità principali passandogli la configurazione dell'utente.
    # L'ID della entry serve a rendere gli Unique ID dei sensori univoci nel sistema.
    energy_sensor = OctopusMonthlyEnergy(hass, config, entry.entry_id)
    cost_sensor = OctopusMonthlyCost(hass, config, entry.entry_id)
    price_sensor = OctopusCurrentPrice(hass, config, entry.entry_id)
    
    # Aggiunge le entità a Home Assistant. 'True' forza un primo aggiornamento immediato.
    async_add_entities([energy_sensor, cost_sensor, price_sensor], True)

class OctopusBaseEntity(SensorEntity):
    """
    Classe base "astratta" per raggruppare le proprietà comuni.
    Viene usata per evitare ripetizioni di codice, specialmente per il Device Info.
    """
    def __init__(self, config):
        self._config = config

    @property
    def device_info(self):
        """
        Definisce come le entità vengono raggruppate sotto un unico 'Dispositivo' nella UI.
        Senza questo, ogni sensore apparirebbe come un'entità slegata.
        """
        # Usiamo l'ID del sensore sorgente per garantire che istanze diverse dell'integrazione
        # creino dispositivi diversi (es. se ho due contatori diversi).
        unique_dev_id = self._config.get(CONF_VALUE_SENSOR, "default")
        
        return {
            "identifiers": {(DOMAIN, f"device_{unique_dev_id}")},
            "name": "Octopus Monitor Elettricità",
            "manufacturer": "Octopus Adapter",
            "model": "Calcolatore Costi Mensili",
            "sw_version": "1.1.1", # Versione utile per il debug e la gestione del parco dispositivi
            "hw_version": "Software",
            "entry_type": "service", # Indica che non è un hardware fisico ma un servizio virtuale
        }

class OctopusCurrentPrice(OctopusBaseEntity):
    """
    Sensore che espone il prezzo attuale applicato per kWh.
    Gestisce sia il prezzo fisso (da configurazione) che quello dinamico (da sensore esterno).
    """

    def __init__(self, hass, config, entry_id):
        super().__init__(config)
        self.hass = hass
        self._attr_name = "Octopus Prezzo Attuale"
        self._attr_unique_id = f"octopus_current_price_{entry_id}"
        self._attr_state_class = SensorStateClass.MEASUREMENT # Indica che il valore può fluttuare
        self._attr_native_unit_of_measurement = "EUR/kWh"
        self._state = 0.0

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        """Chiamato quando il sensore viene aggiunto a HA. Gestisce i listener."""
        # Se la tariffa è dinamica, dobbiamo "osservare" il sensore del prezzo per reagire ai cambi.
        if self._config.get(CONF_PRICE_TYPE) != PRICE_TYPE_FIXED:
            p_src = self._config.get(CONF_PRICE_SENSOR)
            if p_src:
                self.async_on_remove(
                    async_track_state_change_event(self.hass, [p_src], self._async_on_price_change)
                )
        await self.async_update()

    async def _async_on_price_change(self, event):
        """Reazione al cambiamento di stato del sensore di prezzo esterno."""
        await self.async_update()
        self.async_write_ha_state() # Forza l'aggiornamento nella UI
        # Notifica il sensore Costo che il prezzo è cambiato, quindi deve ricalcolare.
        async_dispatcher_send(self.hass, SIGNAL_PRICE_UPDATE)

    async def async_update(self):
        """Aggiorna il valore interno leggendo dalla config o dallo stato di HA."""
        self._state = await self._get_current_price()

    async def _get_current_price(self):
        """Logica di recupero del prezzo basata sulla scelta dell'utente."""
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        
        p_src = self._config.get(CONF_PRICE_SENSOR)
        if p_src:
            st = self.hass.states.get(p_src)
            # Verifica che il sensore esista e abbia un valore valido (non 'unavailable')
            if st and st.state not in ["unknown", "unavailable"]:
                try:
                    return float(st.state)
                except ValueError:
                    return 0.0
        return 0.0

class OctopusMonthlyEnergy(OctopusBaseEntity):
    """
    Sensore Energia: Si occupa di salvare i dati giornalieri su JSON e 
    calcolare quanto consumato dall'inizio del mese corrente ad oggi.
    """

    def __init__(self, hass, config, entry_id):
        super().__init__(config)
        self.hass = hass
        self._attr_name = "Octopus Energia Mensile"
        self._attr_unique_id = f"octopus_monthly_energy_{entry_id}"
        self._attr_device_class = SensorDeviceClass.ENERGY # Fondamentale per la compatibilità col pannello Energy
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "kWh"
        self._state = 0.0

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        """Inizializzazione: Carica i dati dal file e imposta il monitoraggio dei sensori sorgente."""
        # Carica il database JSON in memoria per calcolare il valore iniziale.
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        if data:
            self._state = self._calculate_monthly_value(data)
            price = await self._get_current_price()
            # Carica le statistiche storiche di HA (Long Term Statistics) per popolare i grafici.
            self.hass.async_create_task(push_bulk_statistics(self.hass, data, price))
            # Notifica il sensore costo del valore attuale.
            async_dispatcher_send(self.hass, SIGNAL_ENERGY_UPDATE, self._state)

        # Traccia il sensore della data e dei kWh totali.
        data_src = self._config.get(CONF_DATA_SENSOR)
        value_src = self._config.get(CONF_VALUE_SENSOR)
        self.async_on_remove(
            async_track_state_change_event(self.hass, [data_src, value_src], self._async_on_dependency_update)
        )

    def _calculate_monthly_value(self, data):
        """
        Calcola il consumo mensile: Sottrae dal valore dell'ultima lettura 
        il valore presente all'ultimo giorno del mese precedente.
        """
        if not data: return 0.0
        sorted_dates = sorted(data.keys())
        last_total = data[sorted_dates[-1]] # Valore cumulativo più recente
        
        # Genera la stringa del primo giorno del mese attuale (es: 2024-05-01)
        first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        base_value = 0.0
        # Cerchiamo a ritroso nel JSON l'ultima lettura utile prima dell'inizio del mese.
        for d in reversed(sorted_dates):
            if d < first_of_month:
                base_value = data[d]
                break
        
        # Se non troviamo letture del mese precedente, base_value rimane 0.0
        return round(last_total - base_value, 3)

    async def _async_on_dependency_update(self, event):
        """Chiamato ogni volta che il sensore data o il sensore kWh cambiano."""
        await self.async_update()
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_ENERGY_UPDATE, self._state)

    async def async_update(self):
        """Logica principale di salvataggio dati giornalieri con protezione spike."""
        try:
            d_st = self.hass.states.get(self._config.get(CONF_DATA_SENSOR))
            v_st = self.hass.states.get(self._config.get(CONF_VALUE_SENSOR))
            
            if not d_st or not v_st or d_st.state in ["unknown", "unavailable"]: 
                return

            # Trasforma il formato data da quello del sensore (DD/MM/YYYY) a quello ISO (YYYY-MM-DD) per il JSON.
            reading_date = datetime.strptime(d_st.state, "%d/%m/%Y").strftime("%Y-%m-%d")
            
            try:
                daily_val = float(v_st.state)
            except ValueError:
                return

            # --- INIZIO PATCH VALIDAZIONE (v1.1.1) ---
            # Protezione contro letture sporche dell'integrazione Octopus
            if daily_val < 0:
                _LOGGER.warning(f"Scartata lettura negativa anomala: {daily_val} il {reading_date}. Verificare sensore sorgente.")
                return

            if daily_val > 150: # Limite di sicurezza: scarta letture sopra i 150kWh in un solo giorno
                _LOGGER.error(f"Scartata lettura sospetta troppo alta: {daily_val} kWh il {reading_date}.")
                return
            # --- FINE PATCH VALIDAZIONE ---

            # Operazione I/O: Carica JSON. Usiamo executor_job per non bloccare l'interfaccia.
            data = await self.hass.async_add_executor_job(load_data_sync, self.hass)

            # Se questa data non è ancora nel database, la aggiungiamo.
            if not has_date(data, reading_date):
                # Recupera l'ultimo totale cumulativo salvato.
                last_cum = data[sorted(data.keys())[-1]] if data else 0.0
                
                # Calcola il nuovo totale cumulativo sommando il consumo odierno all'ultimo totale.
                new_cum = round(last_cum + daily_val, 3)
                
                # Aggiorna il database e salva su disco.
                add_day(data, reading_date, new_cum)
                await self.hass.async_add_executor_job(save_data_sync, self.hass, data)

                # Invia il nuovo punto dati alle statistiche a lungo termine di HA.
                price = await self._get_current_price()
                await push_statistics(self.hass, reading_date, new_cum, price)
                
                # Ricalcola lo stato del sensore per riflettere il nuovo valore mensile.
                self._state = self._calculate_monthly_value(data)
                
        except Exception as e:
            _LOGGER.error("Errore durante l'aggiornamento dei dati energia: %s", e)

    async def _get_current_price(self):
        """Helper interno per ottenere il prezzo da associare alla statistica dell'energia."""
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        p_src = self._config.get(CONF_PRICE_SENSOR)
        if p_src:
            st = self.hass.states.get(p_src)
            if st and st.state not in ["unknown", "unavailable"]:
                try:
                    return float(st.state)
                except ValueError:
                    return 0.0
        return 0.0

class OctopusMonthlyCost(OctopusBaseEntity):
    """
    Sensore Costo: Calcola il costo monetario (Energia Mensile * Prezzo Corrente).
    Reagisce in tempo reale sia ai cambi di consumo che ai cambi di prezzo.
    """

    def __init__(self, hass, config, entry_id):
        super().__init__(config)
        self.hass = hass
        self._attr_name = "Octopus Costo Mensile"
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
        """Aggiunge dettagli tecnici visibili cliccando sul sensore nella UI."""
        return {
            "current_price": self._current_price,
            "price_unit": "EUR/kWh",
            "last_energy_reading": self._last_energy
        }

    async def async_added_to_hass(self):
        """Si collega ai segnali degli altri sensori."""
        # Si mette in ascolto: se gli altri sensori (Energia o Prezzo) dicono di essere cambiati, rinfresca il costo.
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_ENERGY_UPDATE, self._update_from_energy))
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_PRICE_UPDATE, self._update_from_price))
        
        # Caricamento iniziale per non partire da 0.
        data = await self.hass.async_add_executor_job(load_data_sync, self.hass)
        if data:
            self._last_energy = self._calculate_current_monthly_energy(data)
            await self._refresh_cost()

    def _calculate_current_monthly_energy(self, data):
        """Calcolo identico a quello del sensore Energia per coerenza dati."""
        sorted_dates = sorted(data.keys())
        if not sorted_dates: return 0.0
        last_total = data[sorted_dates[-1]]
        first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        base = 0.0
        for d in reversed(sorted_dates):
            if d < first_of_month:
                base = data[d]
                break
        return round(last_total - base, 3)

    async def _update_from_energy(self, energy_val):
        """Triggerato dal dispatcher quando il sensore Energia termina un aggiornamento."""
        self._last_energy = energy_val
        await self._refresh_cost()

    async def _update_from_price(self):
        """Triggerato dal dispatcher quando il sensore Prezzo rileva un cambio tariffa."""
        await self._refresh_cost()

    async def _refresh_cost(self):
        """Esegue il calcolo matematico finale."""
        self._current_price = await self._get_current_price()
        # Costo = kWh del mese * prezzo attuale.
        self._state = round(self._last_energy * self._current_price, 2)
        self.async_write_ha_state()

    async def _get_current_price(self):
        """Recupera il prezzo attuale per il calcolo del costo."""
        if self._config.get(CONF_PRICE_TYPE) == PRICE_TYPE_FIXED:
            return float(self._config.get(CONF_FIXED_PRICE, 0.0))
        p_src = self._config.get(CONF_PRICE_SENSOR)
        if p_src:
            st = self.hass.states.get(p_src)
            if st and st.state not in ["unknown", "unavailable"]:
                try:
                    return float(st.state)
                except ValueError:
                    return 0.0
        return 0.0