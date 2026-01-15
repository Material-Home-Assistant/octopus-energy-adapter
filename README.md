# 🐙 Octopus Energy Adapter for Home Assistant

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=%E2%98%95&slug=giovannilamarmora&button_colour=5F7FFF&font_colour=ffffff&font_family=Poppins&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/giovannilamarmora)

[![Instagram](https://img.shields.io/badge/Instagram-%40gio_lamarmora-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/gio_lamarmora/)&nbsp;&nbsp;[![WebSite](https://img.shields.io/badge/WebSite%20-Visit-blue?style=for-the-badge&logo=Google-Chrome&logoColor=white)](https://giovannilamarmora.github.io/)&nbsp;&nbsp;[![BuyMeACoffee](https://img.shields.io/badge/☕_Buy_me_a_coffee-Support-orange?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://www.buymeacoffee.com/giovannilamarmora)&nbsp;&nbsp;[![Sponsor](https://img.shields.io/badge/GitHub_Sponsors-Become_a_Sponsor-pink?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/giovannilamarmora)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge&logo=hacs&logoColor=white)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-1.1.1-blue.svg?style=for-the-badge)
![Home Assistant](https://img.shields.io/badge/Home--Assistant-2025.1.0%2B-blueviolet.svg?style=for-the-badge&logo=home-assistant&logoColor=white)

**Integra i consumi storici di Octopus Energy direttamente nel Pannello Energia di Home Assistant.**

Questo adapter risolve il problema del ritardo nella ricezione dei dati, permettendo un'analisi precisa e puntuale dei consumi energetici.

---

## ✨ Caratteristiche Principali

<div align="center">

<table style="border-radius: 28px; overflow: hidden; border-collapse: separate; border-spacing: 0; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
<tr>
<td width="25%" align="center" style="padding: 32px 20px; background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);">
<div style="font-size: 48px; margin-bottom: 12px;">📊</div>
<strong style="font-size: 16px; color: #1565C0;">Importazione Storica</strong><br/><br/>
<span style="color: #424242; font-size: 14px;">Carica i dati passati e li inietta nel database delle statistiche a lungo termine.</span>
</td>
<td width="25%" align="center" style="padding: 32px 20px; background: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%);">
<div style="font-size: 48px; margin-bottom: 12px;">🔄</div>
<strong style="font-size: 16px; color: #6A1B9A;">Sync Automatica</strong><br/><br/>
<span style="color: #424242; font-size: 14px;">Si aggiorna ogni volta che i sensori ufficiali Octopus ricevono nuovi dati.</span>
</td>
<td width="25%" align="center" style="padding: 32px 20px; background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);">
<div style="font-size: 48px; margin-bottom: 12px;">💰</div>
<strong style="font-size: 16px; color: #2E7D32;">Supporto Costi</strong><br/><br/>
<span style="color: #424242; font-size: 14px;">Calcola il costo totale in Euro basandosi su tariffe fisse o dinamiche.</span>
</td>
<td width="25%" align="center" style="padding: 32px 20px; background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);">
<div style="font-size: 48px; margin-bottom: 12px;">⚡</div>
<strong style="font-size: 16px; color: #E65100;">Energy Dashboard</strong><br/><br/>
<span style="color: #424242; font-size: 14px;">Entità native ottimizzate per il Pannello Energia di Home Assistant.</span>
</td>
</tr>
</table>

</div>

---

## 🗂 Archiviazione Dati

L'integrazione salva lo storico calcolato nel seguente percorso locale per garantire la persistenza dei dati:
`/config/octopus_data/octopus_energy.json`

---

## 📦 Installazione

### 🚀 Metodo 1 – Installazione via HACS (Consigliato)

1. Assicurati che [HACS](https://hacs.xyz/) sia installato.
2. Apri **HACS** -> **Integrazioni**.
3. Clicca sui tre puntini in alto a destra e seleziona **Repository personalizzati**.
4. Incolla l'URL: `https://github.com/HA-Material-Components/octopus-energy-adapter`
5. Seleziona **Integrazione** come categoria e clicca su **Aggiungi**.
6. Clicca su **Scarica** e riavvia Home Assistant.

### 🔧 Metodo 2 – Installazione Manuale

1. Scarica l'ultima release.
2. Copia la cartella `custom_components/octopus_energy_adapter` nella tua cartella `custom_components`.
3. Riavvia Home Assistant.

---

## ⚙️ Configurazione

1. Vai in **Impostazioni** -> **Dispositivi e Servizi**.
2. Clicca su **Aggiungi Integrazione** e cerca `Octopus Energy Adapter`.
3. Configura i sensori richiesti:
   - **Sensore Data:** Il sensore che indica la fine dell'intervallo (es. `last_interval_end`).
   - **Sensore Valore:** Il sensore che fornisce il consumo in kWh dell'ultimo intervallo.
   - **Prezzo:** Imposta un valore fisso o un sensore di prezzo (EUR/kWh).

### 📊 Configurazione Pannello Energia

Per popolare i grafici:

1. Vai nella dashboard **Energia** -> **Configurazione**.
2. Aggiungi `Octopus Total Energy` sotto **Consumo di rete**.
3. Associa `Octopus Total Cost` per il monitoraggio dei costi.

---

## 🛠 Troubleshooting

<div align="center">

<table style="border-radius: 28px; overflow: hidden; border-collapse: separate; border-spacing: 0; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
<tr>
<td align="center" style="padding: 32px; background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);">
<strong style="font-size: 18px; color: #C62828;">Grafici vuoti?</strong>
<p style="color: #424242; margin-top: 12px;">
Dopo la prima configurazione, attendi almeno <strong>60-120 minuti</strong> per il primo ciclo di calcolo orario di Home Assistant.
</p>
</td>
</tr>
</table>

</div>

---

## 💝 Supporta il Progetto

<div align="center">

Se questo progetto ti è stato utile, considera di supportarlo!

<table style="border-radius: 28px; overflow: hidden; border-collapse: separate; border-spacing: 0; box-shadow: 0 8px 32px rgba(255, 221, 0, 0.2); max-width: 700px; margin: 24px auto;">
<tr>
<td align="center" style="padding: 48px 40px; background: linear-gradient(135deg, #FFEB3B 0%, #FFC107 100%);">
<div style="font-size: 64px; margin-bottom: 16px;">☕</div>
<h3 style="color: #F57F17; margin: 0 0 24px 0; font-size: 24px;">Offrimi un Caffè</h3>

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=%E2%98%95&slug=giovannilamarmora&button_colour=F57F17&font_colour=000000&font_family=Poppins&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/giovannilamarmora)

<br/>
<p style="margin-top: 24px; color: #424242; font-size: 14px; line-height: 1.6;">
<strong>Il tuo supporto aiuta a mantenere vivo il progetto!</strong><br/>
⭐ Lascia una stella su GitHub se ti piace
</p>
</td>
</tr>
</table>

</div>

---

## 📜 Licenza

<div align="center">

<table style="border-radius: 28px; overflow: hidden; border-collapse: separate; border-spacing: 0; box-shadow: 0 4px 24px rgba(0,0,0,0.08); max-width: 400px; margin: 0 auto;">
<tr>
<td align="center" style="padding: 32px; background: linear-gradient(135deg, #E1F5FE 0%, #B3E5FC 100%);">
<a href="https://www.apache.org/licenses/LICENSE-2.0">
<img src="https://img.shields.io/badge/License-Apache_2.0-0277BD.svg?style=for-the-badge" alt="License: Apache 2.0" style="border-radius: 8px;"/>
</a>
<p style="margin-top: 16px; color: #424242; font-size: 14px;">
<strong>Libero di usare, modificare e distribuire sotto licenza Apache 2.0</strong>
</p>
</td>
</tr>
</table>

</div>
