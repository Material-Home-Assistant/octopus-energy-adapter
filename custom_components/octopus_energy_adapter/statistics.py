from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.util.dt import as_utc
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

async def push_statistics(hass, date_str, cumulative_value, price):
    """Invia un singolo punto statistico per energia e costo."""
    await push_bulk_statistics(hass, {date_str: cumulative_value}, price)

async def push_bulk_statistics(hass, data_dict, price):
    """Invia più punti statistici (storico) per energia e costo."""
    energy_id = "sensor:octopus_energy_total"
    cost_id = "sensor:octopus_energy_cost_total"
    
    # Metadata per il sensore di Energia (kWh)
    energy_metadata = {
        "has_mean": False,
        "has_sum": True,
        "name": "Octopus Total Energy",  # Nome in inglese
        "source": "sensor",
        "statistic_id": energy_id,
        "unit_of_measurement": "kWh",
    }

    # Metadata per il sensore di Costo (EUR)
    cost_metadata = {
        "has_mean": False,
        "has_sum": True,
        "name": "Octopus Total Cost",    # Nome in inglese
        "source": "sensor",
        "statistic_id": cost_id,
        "unit_of_measurement": "EUR",
    }

    energy_stats = []
    cost_stats = []
    sorted_dates = sorted(data_dict.keys())

    for date_str in sorted_dates:
        # Valore energia
        cumulative_energy = round(float(data_dict[date_str]), 3)
        # Calcolo costo (accumulato)
        cumulative_cost = round(cumulative_energy * float(price), 2)
        
        # Timestamp a mezzanotte spaccata (obbligatorio per HA)
        dt_local = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_time = as_utc(dt_local)

        energy_stats.append({
            "start": start_time,
            "last_reset": None,
            "sum": cumulative_energy
        })
        
        cost_stats.append({
            "start": start_time,
            "last_reset": None,
            "sum": cumulative_cost
        })

    if energy_stats:
        _LOGGER.info(f"Inviate statistiche energia a {energy_id} (prezzo applicato: {price})")
        async_add_external_statistics(hass, energy_metadata, energy_stats)
        
    if cost_stats:
        _LOGGER.info(f"Inviate statistiche costo a {cost_id}")
        async_add_external_statistics(hass, cost_metadata, cost_stats)