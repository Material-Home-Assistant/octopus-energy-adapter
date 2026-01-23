"""
Questo modulo gestisce il flusso di configurazione (Config Flow) per Octopus Energy Adapter.
Permette all'utente di impostare i sensori sorgente e il tipo di tariffa tramite l'interfaccia di HA.
"""

import voluptuous as vol  # Libreria per la validazione dei dati
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector  # Permette di creare selettori grafici (es. lista entità)
from .const import (
    DOMAIN,
    CONF_DATA_SENSOR,
    CONF_VALUE_SENSOR, 
    CONF_PRICE_TYPE, 
    CONF_FIXED_PRICE, 
    CONF_PRICE_SENSOR,
    PRICE_TYPE_FIXED, 
    PRICE_TYPE_SENSOR
)

class OctopusAdapterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Gestisce la prima installazione dell'integrazione.
    Viene attivato quando l'utente clicca su 'Aggiungi Integrazione'.
    """
    VERSION = 1 # Versione dello schema dati (utile se in futuro cambiano i campi)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """
        Abilita il pulsante 'Configura' sull'integrazione già installata.
        Senza questo metodo, non potresti modificare i sensori in un secondo momento.
        """
        return OctopusOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """
        Gestisce il primo (e unico) step della configurazione iniziale.
        """
        errors = {} # Dizionario per memorizzare errori di validazione da mostrare all'utente

        # Questo blocco viene eseguito solo quando l'utente preme il tasto 'Invia'
        if user_input is not None:
            # Recuperiamo il tipo di prezzo scelto per validare i campi dipendenti
            price_type = user_input.get(CONF_PRICE_TYPE)
            
            # VALIDAZIONE MANUALE:
            # Poiché nel form mostriamo sia Prezzo Fisso che Sensore, dobbiamo assicurarci
            # che l'utente abbia compilato quello corretto in base alla sua scelta.
            if price_type == PRICE_TYPE_FIXED and not user_input.get(CONF_FIXED_PRICE):
                # Se manca il valore numerico, restituiamo un errore riferito alla chiave nel file lingue
                errors["base"] = "missing_fixed_price"
            elif price_type == PRICE_TYPE_SENSOR and not user_input.get(CONF_PRICE_SENSOR):
                # Se manca il sensore dinamico, restituiamo l'errore corrispondente
                errors["base"] = "missing_price_sensor"
            
            # Se non ci sono errori, creiamo ufficialmente l'istanza dell'integrazione
            if not errors:
                return self.async_create_entry(title="Octopus Energy", data=user_input)

        # Mostriamo il modulo (form) all'utente.
        # Usiamo vol.Schema per definire quali campi appariranno nella finestra popup.
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                # Selettore per l'entità che fornisce la data della lettura
                vol.Required(CONF_DATA_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                # Selettore per l'entità che fornisce il consumo in kWh
                vol.Required(CONF_VALUE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                # Menu a tendina per scegliere tra Prezzo Fisso o Sensore Dinamico
                vol.Required(CONF_PRICE_TYPE, default=PRICE_TYPE_FIXED): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[PRICE_TYPE_FIXED, PRICE_TYPE_SENSOR],
                        mode=selector.SelectSelectorMode.LIST
                    )
                ),
                # Campo numerico (opzionale nello schema per evitare errori 400 se vuoto)
                vol.Optional(CONF_FIXED_PRICE, default=0.0): vol.Coerce(float),
                # Selettore entità per il prezzo dinamico
                vol.Optional(CONF_PRICE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }),
            errors=errors # Passiamo gli eventuali errori riscontrati per visualizzarli in rosso
        )

class OctopusOptionsFlowHandler(config_entries.OptionsFlow):
    """
    Gestisce la modifica di un'integrazione esistente.
    """
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Inizializza il flusso delle opzioni."""
        # Rimuoviamo self.config_entry = config_entry perché causa il crash
        # Se serve riferirsi alla entry, si usa self.config_entry che è già ereditato
        pass

    async def async_step_init(self, user_input=None):
        """
        Punto di ingresso quando l'utente preme 'Configura'.
        """
        errors = {}
        
        # In OptionsFlow, l'oggetto entry è accessibile tramite self.config_entry
        config_entry = self.config_entry

        if user_input is not None:
            price_type = user_input.get(CONF_PRICE_TYPE)
            
            if price_type == PRICE_TYPE_FIXED and not user_input.get(CONF_FIXED_PRICE):
                errors["base"] = "missing_fixed_price"
            elif price_type == PRICE_TYPE_SENSOR and not user_input.get(CONF_PRICE_SENSOR):
                errors["base"] = "missing_price_sensor"

            if not errors:
                # Aggiorniamo i DATI della config entry (non le opzioni separate)
                # NOTA: async_update_entry ricaricherà l'integrazione automaticamente
                self.hass.config_entries.async_update_entry(config_entry, data=user_input)
                return self.async_create_entry(title="", data=user_input)

        # Recuperiamo i dati attuali dai dati della entry
        current_data = config_entry.data
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_DATA_SENSOR, default=current_data.get(CONF_DATA_SENSOR, "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_VALUE_SENSOR, default=current_data.get(CONF_VALUE_SENSOR, "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_PRICE_TYPE, default=current_data.get(CONF_PRICE_TYPE, PRICE_TYPE_FIXED)): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[PRICE_TYPE_FIXED, PRICE_TYPE_SENSOR],
                        mode=selector.SelectSelectorMode.LIST
                    )
                ),
                vol.Optional(CONF_FIXED_PRICE, default=current_data.get(CONF_FIXED_PRICE, 0.0)): vol.Coerce(float),
                vol.Optional(CONF_PRICE_SENSOR, default=current_data.get(CONF_PRICE_SENSOR, "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }),
            errors=errors
        )