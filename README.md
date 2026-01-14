# Octopus Energy Adapter for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home--Assistant-2025.1.0%2B-blueviolet.svg)

Questo adapter personalizzato permette di integrare i consumi storici di **Octopus Energy** direttamente nel **Pannello Energia** di Home Assistant, risolvendo il problema del ritardo nella ricezione dei dati.

## ✨ Caratteristiche

- **Importazione Storica:** Carica i dati passati e li inietta nel database delle statistiche a lungo termine.
- **Sincronizzazione Automatica:** Si aggiorna ogni volta che i sensori ufficiali Octopus ricevono nuovi dati.
- **Supporto Costi:** Calcola il costo totale in Euro basandosi su tariffe fisse o sensori di prezzo dinamici.
- **Ottimizzato per il Pannello Energia:** Entità native con `device_class: energy` e `monetary`.

## 🗂 Archiviazione Dati

L'integrazione salva lo storico calcolato nel seguente percorso locale:
`/config/octopus_data/octopus_energy.json`

Questo file permette all'integrazione di mantenere la coerenza dei dati anche in caso di reinstallazione o pulizia del database di Home Assistant.

## 🚀 Installazione via HACS

1. Assicurati che [HACS](https://hacs.xyz/) sia installato.
2. Apri **HACS** -> **Integrazioni**.
3. Clicca sui tre puntini in alto a destra e seleziona **Repository personalizzati**.
4. Incolla l'URL: `https://github.com/HA-Material-Components/octopus-energy-adapter`
5. Seleziona **Integrazione** come categoria e clicca su **Aggiungi**.
6. Clicca su **Scarica** e riavvia Home Assistant.

## ⚙️ Configurazione

1. Vai in **Impostazioni** -> **Dispositivi e Servizi**.
2. Clicca su **Aggiungi Integrazione** e cerca `Octopus Energy Adapter`.
3. Configura i sensori richiesti:
   - **Sensore Data:** Il sensore che indica la fine dell'intervallo (es. `last_interval_end`).
   - **Sensore Valore:** Il sensore che fornisce il consumo in kWh dell'ultimo intervallo.
   - **Prezzo:** Imposta un valore fisso o un sensore di prezzo (EUR/kWh).

## 📊 Configurazione Pannello Energia

Per popolare i grafici:

1. Vai nella dashboard **Energia** -> **Configurazione**.
2. Aggiungi `Octopus Total Energy` sotto **Consumo di rete**.
3. Associa `Octopus Total Cost` per il monitoraggio dei costi.

## 🛠 Troubleshooting

- **Grafici vuoti:** Dopo la prima configurazione, attendi almeno 60-120 minuti per il primo ciclo di calcolo orario di Home Assistant.
