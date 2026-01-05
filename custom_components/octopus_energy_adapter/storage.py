import json
import os
import logging

_LOGGER = logging.getLogger(__name__)
STORAGE_FILE = "octopus_energy.json"

def load_data_sync(hass):
    """Questa è una funzione sincrona che legge il file."""
    path = hass.config.path(STORAGE_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        _LOGGER.error(f"Errore durante la lettura del file JSON: {e}")
        return {}

def save_data_sync(hass, data):
    """Questa è una funzione sincrona che scrive il file."""
    path = hass.config.path(STORAGE_FILE)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        _LOGGER.error(f"Errore durante il salvataggio del file JSON: {e}")

def has_date(data, date_str):
    return date_str in data

def add_day(data, date_str, cumulative_value):
    data[date_str] = cumulative_value