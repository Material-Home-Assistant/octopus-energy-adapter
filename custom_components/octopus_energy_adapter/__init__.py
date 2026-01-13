"""
Questo è il file principale dell'integrazione (Entry Point).
Gestisce il ciclo di vita dell'integrazione: caricamento, aggiornamento delle opzioni e rimozione.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Viene chiamato ogni volta che Home Assistant si avvia o quando viene 
    aggiunta una nuova istanza dell'integrazione tramite l'interfaccia utente.
    """
    
    # Crea un'area di memoria sicura (dizionario) dove l'integrazione può salvare dati temporanei.
    # setdefault assicura che se DOMAIN non esiste nel dizionario globale hass.data, venga creato.
    hass.data.setdefault(DOMAIN, {})
    
    # Memorizziamo i dati della configurazione (sensori scelti, prezzi, ecc.) 
    # associandoli all'ID univoco di questa specifica installazione.
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Registra un 'listener' (ascoltatore): se l'utente va nelle opzioni e cambia un sensore 
    # o il prezzo, viene chiamata automaticamente la funzione 'update_listener'.
    # async_on_unload assicura che questo ascoltatore venga rimosso se l'integrazione viene disinstallata.
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    # Inoltra la configurazione alla piattaforma 'sensor'.
    # Questo comando dice a HA di andare a cercare il file 'sensor.py' e di avviare il setup dei sensori.
    # Nelle versioni recenti di HA si usa async_forward_entry_setups (al plurale).
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    # Restituire True conferma a Home Assistant che l'integrazione è stata avviata con successo.
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Viene chiamato quando l'utente rimuove l'integrazione o la disabilita.
    Serve a 'pulire' il sistema per non lasciare processi o dati orfani in memoria.
    """
    
    # Comunica alla piattaforma 'sensor' di spegnersi e rimuovere le entità dalla dashboard.
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    
    # Se la disattivazione dei sensori è andata a buon fine, rimuoviamo i dati dalla memoria RAM.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """
    Questa funzione viene chiamata ogni volta che l'utente preme 'Salva' nelle opzioni.
    Invece di gestire manualmente i cambi, la soluzione più pulita e sicura è ricaricare l'intera entry.
    """
    # Forza il riavvio dell'istanza dell'integrazione (scarica e ricarica i sensori).
    await hass.config_entries.async_reload(entry.entry_id)