import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    DOMAIN, CONF_DATA_SENSOR, CONF_VALUE_SENSOR, 
    CONF_PRICE_TYPE, CONF_FIXED_PRICE, CONF_PRICE_SENSOR,
    PRICE_TYPE_FIXED, PRICE_TYPE_SENSOR
)

class OctopusAdapterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il Config Flow per Octopus Energy Adapter."""
    VERSION = 1

    def __init__(self):
        """Inizializza il flow."""
        self.data = {}

    async def async_step_user(self, user_input=None):
        """Primo step: Selezione sensori e tipo di prezzo."""
        if user_input is not None:
            self.data.update(user_input)
            # Passa allo step successivo per configurare il prezzo specifico
            return await self.async_step_price()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DATA_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_VALUE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_PRICE_TYPE, default=PRICE_TYPE_FIXED): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[PRICE_TYPE_FIXED, PRICE_TYPE_SENSOR],
                        mode=selector.SelectSelectorMode.LIST
                    )
                ),
            })
        )

    async def async_step_price(self, user_input=None):
        """Secondo step: Mostra solo il campo necessario."""
        errors = {}
        price_type = self.data.get(CONF_PRICE_TYPE)

        if user_input is not None:
            # Salvataggio finale
            return self.async_create_entry(title="Octopus Energy Adapter", data=self.data | user_input)

        # Definiamo i campi dinamicamente
        fields = {}
        if price_type == PRICE_TYPE_FIXED:
            # Usiamo un selettore numerico per maggiore compatibilità
            fields[vol.Required(CONF_FIXED_PRICE)] = selector.NumberSelector(
                selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, unit_of_measurement="€/kWh", step=0.001)
            )
        else:
            fields[vol.Required(CONF_PRICE_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        return self.async_show_form(
            step_id="price",
            data_schema=vol.Schema(fields),
            errors=errors
        )