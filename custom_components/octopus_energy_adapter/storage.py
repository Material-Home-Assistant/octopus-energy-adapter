"""
Questo modulo gestisce la lettura e la scrittura dei dati su file locale (JSON).
I dati vengono salvati nella cartella /config/octopus_data/ per evitare di perdere lo storico.
"""

import json
import os
import logging

_LOGGER = logging.getLogger(__name__)

# Nome del file e della cartella relativa alla cartella /config di Home Assistant
STORAGE_FILE = "octopus_data/octopus_energy.json"

def load_data_sync(hass):
    """
    Legge i dati dal file JSON in modo sincrono.
    Restituisce un dizionario vuoto se il file non esiste o è corrotto.
    """
    # Converte il percorso relativo in un percorso assoluto del sistema (es: /config/...)
    path = hass.config.path(STORAGE_FILE)
    
    # Se il file non esiste ancora (es: prima installazione), restituiamo un dizionario vuoto
    if not os.path.exists(path):
        _LOGGER.debug(f"Il file {path} non esiste ancora. Verrà creato al primo salvataggio.")
        return {}
        
    try:
        # Apriamo il file in modalità lettura con codifica UTF-8
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        # Se il file è corrotto (es: interruzione di corrente durante il salvataggio), logghiamo l'errore
        _LOGGER.error(f"Errore durante la lettura del file JSON: {e}")
        return {}

def save_data_sync(hass, data):
    """
    Salva i dati nel file JSON in modo sincrono.
    Se la cartella non esiste, viene creata automaticamente.
    """
    # Definisce il percorso assoluto: /config/octopus_data/octopus_energy.json
    path = hass.config.path(STORAGE_FILE)
    
    try:
        # Crea la cartella 'octopus_data' se non esiste (exist_ok=True evita errori se esiste già)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Scrive effettivamente il dizionario 'data' nel file JSON.
        # indent=4 rende il file leggibile anche da un essere umano se aperto con un editor.
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
    except Exception as e:
        # Usiamo il logger ufficiale di Home Assistant per tracciare i problemi di scrittura
        _LOGGER.error(f"Errore critico durante il salvataggio dei dati Octopus: {e}")

def has_date(data, date_str):
    """
    Controlla se una specifica data (chiave) è già presente nel database JSON.
    Serve a evitare di sovrascrivere o duplicare letture per lo stesso giorno.
    """
    return date_str in data

def add_day(data, date_str, cumulative_value):
    """
    Aggiunge o aggiorna una lettura nel dizionario in memoria.
    La chiave è la data (YYYY-MM-DD), il valore è il totale kWh cumulativo.
    """
    data[date_str] = cumulative_value