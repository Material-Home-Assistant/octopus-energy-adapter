"""
Questo modulo gestisce l'inserimento manuale delle statistiche a lungo termine nel database di Home Assistant.
Utilizza le 'External Statistics', che permettono di iniettare dati storici non legati a un'entità fisica.
"""

from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.util.dt import as_utc
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

async def push_statistics(hass, date_str, cumulative_value, price):
    """
    Invia un singolo punto statistico (tipicamente l'ultimo aggiornamento).
    È un wrapper semplificato che richiama la funzione push_bulk_statistics.
    """
    await push_bulk_statistics(hass, {date_str: cumulative_value}, price)

async def push_bulk_statistics(hass, data_dict, price):
    """
    Invia un set massivo di dati statistici. 
    Utile al primo avvio per caricare tutto lo storico contenuto nel file JSON.
    """
    # Identificativi univoci per le statistiche esterne. 
    # NOTA: Iniziano con 'sensor:' per essere riconosciuti dal pannello Energia.
    energy_id = "sensor:octopus_energy_total"
    cost_id = "sensor:octopus_energy_cost_total"
    
    # Metadata per l'Energia: descrivono la natura del dato a Home Assistant.
    energy_metadata = {
        "has_mean": False, # Non è una media (es. temperatura)
        "has_sum": True,   # È una somma cumulativa (es. contatore kWh)
        "name": "Octopus Total Energy",
        "source": "sensor", # Indica che il dato proviene da un sensore simulato
        "statistic_id": energy_id,
        "unit_of_measurement": "kWh",
    }

    # Metadata per il Costo: descrivono il dato monetario.
    cost_metadata = {
        "has_mean": False,
        "has_sum": True,
        "name": "Octopus Total Cost",
        "source": "sensor",
        "statistic_id": cost_id,
        "unit_of_measurement": "EUR",
    }

    energy_stats = []
    cost_stats = []
    
    # Ordiniamo le date per assicurarci che vengano inserite in sequenza cronologica.
    # Home Assistant richiede che le statistiche siano coerenti nel tempo.
    sorted_dates = sorted(data_dict.keys())

    for date_str in sorted_dates:
        # Conversione dei dati in formati numerici corretti (float)
        cumulative_energy = round(float(data_dict[date_str]), 3)
        # Calcoliamo il costo totale accumulato fino a quel giorno usando il prezzo fornito.
        cumulative_cost = round(cumulative_energy * float(price), 2)
        
        # IMPORTANTE: Home Assistant accetta statistiche esterne solo se associate 
        # a un timestamp preciso (di solito l'inizio dell'ora o del giorno).
        # Qui impostiamo la mezzanotte locale (00:00:00).
        dt_local = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Convertiamo la mezzanotte locale in UTC, come richiesto dal database interno di HA.
        start_time = as_utc(dt_local)

        # Creiamo il pacchetto dati per l'energia
        energy_stats.append({
            "start": start_time,
            "last_reset": None, # Non resettiamo mai il contatore (è un totale assoluto)
            "sum": cumulative_energy # Il valore cumulativo totale
        })
        
        # Creiamo il pacchetto dati per il costo
        cost_stats.append({
            "start": start_time,
            "last_reset": None,
            "sum": cumulative_cost
        })

    # Se abbiamo accumulato dei dati, li iniettiamo nel database del Recorder.
    if energy_stats:
        _LOGGER.info(f"Inviate statistiche energia a {energy_id} (prezzo applicato: {price})")
        # Questa funzione scrive direttamente nel database di Home Assistant
        async_add_external_statistics(hass, energy_metadata, energy_stats)
        
    if cost_stats:
        _LOGGER.info(f"Inviate statistiche costo a {cost_id}")
        async_add_external_statistics(hass, cost_metadata, cost_stats)