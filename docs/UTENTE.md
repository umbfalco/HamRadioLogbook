# Manuale Utente — Ham Radio Logbook

> **Versione:** 1.1 · **Autore:** IU8VBG

---

## Indice

1. [Cos'è Ham Radio Logbook](#1-cosè-ham-radio-logbook)
2. [Registrazione e primo accesso](#2-registrazione-e-primo-accesso)
3. [Interfaccia principale](#3-interfaccia-principale)
4. [Dashboard — il logbook](#4-dashboard--il-logbook)
5. [Registrare un nuovo QSO](#5-registrare-un-nuovo-qso)
6. [Sezione Report](#6-sezione-report)
7. [Mappa QSO](#7-mappa-qso)
8. [Gestione stazione](#8-gestione-stazione)
9. [Esportazione e importazione](#9-esportazione-e-importazione)
10. [Impostazioni](#10-impostazioni)
11. [Sincronizzazione con MapForHam](#11-sincronizzazione-con-mapforham)
12. [Uso offline e PWA](#12-uso-offline-e-pwa)
13. [Domande frequenti (FAQ)](#13-domande-frequenti-faq)

---

## 1. Cos'è Ham Radio Logbook

**Ham Radio Logbook** è un'applicazione web per la gestione del logbook radioamatoriale conforme allo standard **ADIF (Amateur Data Interchange Format)**. Permette di:

- 📋 Registrare i QSO in tempo reale
- 📶 Funzionare **anche senza connessione internet** (modalità offline)
- 🔄 Sincronizzarsi automaticamente con **MapForHam** quando la rete è disponibile
- 📊 Visualizzare report e statistiche della propria attività
- 🗺️ Vedere i QSO sulla mappa con i locator
- 📥 Importare ed esportare il logbook in formato ADIF, CSV e PDF
- 🔧 Gestire la propria attrezzatura (radio, antenne, accessori)
- 👤 Supportare **più utenti** sulla stessa installazione, ciascuno con i propri dati

---

## 2. Registrazione e primo accesso

### Creare un account

1. Aprire il browser e navigare all'indirizzo dell'applicazione (es. `http://localhost:5000`)
2. Fare clic su **"Registrati"** nella pagina di login, oppure navigare direttamente a `/register`
3. Compilare il modulo di registrazione:

| Campo | Obbligatorio | Descrizione |
|-------|:---:|-------------|
| **Nominativo (Callsign)** | ✅ | Il proprio nominativo radioamatoriale (es. IU8VBG). Verrà convertito automaticamente in maiuscolo |
| **Nome e Cognome** | — | Nome completo (opzionale) |
| **Email** | — | Indirizzo email (opzionale, per recupero futuro) |
| **Password** | ✅ | Minimo 8 caratteri |
| **Conferma Password** | ✅ | Deve corrispondere alla password |

4. Fare clic su **"Registrati"**
5. Al completamento, si verrà reindirizzati automaticamente all'applicazione

> **Nota:** Il nominativo è il nome utente dell'account. Se un altro operatore usa la stessa installazione, può registrare il proprio nominativo separato.

### Accedere all'account

1. Aprire la pagina di login (`/login`)
2. Inserire il proprio **nominativo** e **password**
3. Fare clic su **"Accedi"**

Il sistema ricorda la sessione per **7 giorni**. Dopo questo periodo, o dopo aver fatto clic su "Esci", sarà necessario effettuare nuovamente il login.

> ⚠️ **Attenzione:** Dopo 5 tentativi di login errati, l'accesso viene bloccato per 5 minuti per proteggere l'account.

---

## 3. Interfaccia principale

Dopo il login, si accede alla **dashboard** con la barra di navigazione in alto:

```
🔊 HAM RADIO LOGBOOK  |  Logbook  Nuovo QSO  Report  Mappa  Stazione  Esporta  Impostazioni  IU8VBG  Esci
```

- **Logbook** — elenco di tutti i QSO registrati
- **Nuovo QSO** — modulo per aggiungere un contatto
- **Report** — statistiche e grafici
- **Mappa** — visualizzazione geografica dei QSO
- **Stazione** — gestione radio, antenne e accessori
- **Esporta** — download e importazione del logbook
- **Impostazioni** — profilo, credenziali MapForHam, locator
- **IU8VBG** (il proprio nominativo) — mostrato come promemoria dell'utente attivo
- **Esci** — logout

### Indicatori di stato

In alto a destra sono presenti due indicatori:

| Indicatore | Significato |
|-----------|-------------|
| 🟢 verde | Connesso al server |
| 🔴 rosso | Server non raggiungibile (modalità offline) |
| 🔴 `N` in attesa | QSO salvati offline in attesa di sincronizzazione |

---

## 4. Dashboard — il logbook

La dashboard mostra tutti i QSO registrati in una tabella ordinata dal più recente.

### Colonne della tabella

| Colonna | Descrizione |
|---------|-------------|
| Data | Data del QSO (YYYY-MM-DD) |
| Ora | Orario UTC di inizio (HH:MM) |
| Nominativo | Callsign del corrispondente |
| Banda | Banda utilizzata (80m, 40m, 20m, ...) |
| Modo | Modalità (SSB, CW, FT8, FM, ...) |
| RST | RST inviato e ricevuto |
| Nome | Nome del corrispondente |
| QTH | Località del corrispondente |
| Sync | ✓ = sincronizzato con MFH, … = solo locale |
| Azioni | Pulsanti modifica ✏️ ed elimina 🗑️ |

### Ricerca e filtro
Usare la casella di ricerca sopra la tabella per filtrare i QSO per nominativo, nome, banda o qualsiasi altro campo.

### Modificare un QSO
1. Fare clic sull'icona ✏️ nella riga del QSO
2. Il modulo "Nuovo QSO" si aprirà con i dati precompilati
3. Modificare i campi necessari
4. Fare clic su **"Salva QSO"**

### Eliminare un QSO
1. Fare clic sull'icona 🗑️ nella riga del QSO
2. Confermare l'eliminazione
3. Se il QSO era già sincronizzato con MapForHam, verrà eliminato anche lì

---

## 5. Registrare un nuovo QSO

Fare clic su **"Nuovo QSO"** nella barra di navigazione.

### Campi del modulo

**Campi obbligatori** (evidenziati):
- **Data QSO** — precompilata con la data odierna
- **Ora inizio** — precompilata con l'ora UTC corrente
- **Nominativo** — callsign del corrispondente

**Campi facoltativi:**

| Campo | Descrizione |
|-------|-------------|
| Data/Ora fine | Fine del QSO |
| Modo | SSB, CW, FT8, FM, AM, RTTY, JS8, DSTAR, DMR, ecc. |
| Frequenza | In MHz (es. 14.250) |
| Banda | Selezionare dalla lista o inserire manualmente |
| RST inviato/ricevuto | Segnale (59, 579, -10 per FT8, ecc.) |
| Nome | Nome dell'operatore corrispondente |
| QTH | Città/Paese del corrispondente |
| Locator | Maidenhead grid square (es. JN70) |
| Potenza TX | In Watt |
| Commento | Note libere |
| Antenna | Selezionare dall'elenco delle antenne configurate |
| Il mio locator | Locator della propria stazione per questa sessione |

### QRZ Lookup automatico

Dopo aver digitato il nominativo del corrispondente e premuto **Tab** (o aspettato 1 secondo), l'applicazione esegue automaticamente la ricerca:

1. Prima tenta tramite **MapForHam** (se l'API key è configurata)
2. In caso di mancata risposta, usa **HamDB.org** (gratuito, nessuna API key)

Se il nominativo viene trovato, i campi **Nome**, **QTH**, **Locator**, **Paese**, **Zona CQ** e **Zona ITU** vengono compilati automaticamente, mostrando il badge con la fonte (MapForHam o HamDB).

> 💡 **Suggerimento:** Il lookup funziona anche offline se i dati sono già in cache.

### Salvataggio

Fare clic su **"Salva QSO"**. Il sistema:
1. Salva il QSO nel database locale
2. Se l'API MapForHam è configurata, lo sincronizza immediatamente
3. In caso di errore o offline, lo mette in coda per la sincronizzazione successiva

---

## 6. Sezione Report

La sezione Report mostra le statistiche della propria attività radioamatoriale.

### KPI principali (riga 1)

| Card | Contenuto |
|------|-----------|
| **Ultimo QSO** | Nominativo, data, ora, banda, modo dell'ultimo contatto |
| **Banda più usata** | Banda con il maggior numero di QSO (tutti i tempi) |
| **Modo principale** | Modalità operativa più utilizzata |
| **Ore di attività** | Somma delle durate dei QSO con ora di fine registrata |

### Statistiche mensili (riga 2)

| Card | Contenuto |
|------|-----------|
| **QSO del mese** | Conteggio QSO del mese corrente |
| **Distribuzioni** | Grafici a barre per banda e modalità |

### Trend 6 mesi (riga 3)
Grafico del numero di QSO mensili negli ultimi 6 mesi.

### Top 5 DXCC e QSO per antenna (riga 4)
- **Top 5 DXCC**: i paesi/entità più contattati, calcolati automaticamente dal prefisso del nominativo
- **QSO per antenna**: quanti QSO sono stati effettuati con ciascuna antenna configurata nella stazione

---

## 7. Mappa QSO

La sezione Mappa visualizza i QSO su una mappa geografica interattiva.

### Filtro periodo
Selezionare il periodo da visualizzare:
- **Oggi** — solo i QSO del giorno corrente
- **Settimana** — ultimi 7 giorni
- **Mese** — ultimi 30 giorni
- **Tutti** — tutti i QSO nel logbook

### Visualizzazione
- Il **punto blu** al centro rappresenta la propria stazione (basato sul locator configurato)
- Le **linee colorate** collegano la propria stazione al locator del corrispondente
- Il colore della linea dipende dalla **banda** utilizzata:

| Colore | Banda |
|--------|-------|
| 🔴 Rosso | 80m |
| 🟠 Arancione | 40m |
| 🟡 Giallo | 20m |
| 🟢 Verde | 15m |
| 🔵 Azzurro | 10m |

- Fare clic su un **marcatore** sul corrispondente per vedere i dettagli del QSO

> 💡 **Nota:** Solo i QSO con il **locator del corrispondente** compariranno sulla mappa. Inserire sempre il locator quando si registra un QSO per ottenere una mappa completa.

### Statistiche della mappa
In basso alla mappa vengono mostrate:
- Totale QSO nel periodo
- QSO con locator (visibili sulla mappa)
- Numero di paesi differenti
- Banda e modo più usati nel periodo

---

## 8. Gestione stazione

La sezione **Stazione** permette di catalogare la propria attrezzatura radio.

### Categorie di attrezzatura

| Tipo | Esempi |
|------|--------|
| **Radio** | ICOM IC-7300, Yaesu FT-991A, Kenwood TS-590 |
| **Antenna** | Dipolo, Yagi, Verticale, Loop |
| **Accessorio** | Tuner, Amplificatore, Filtro, TRX |

### Aggiungere un elemento

1. Fare clic su **"+ Aggiungi Attrezzatura"**
2. Compilare il modulo:
   - **Tipo** — categoria (radio/antenna/accessorio)
   - **Nome** — denominazione dell'elemento (obbligatorio)
   - **Marca e Modello** — produttore e numero di modello
   - **Copertura bande** — es. "HF 160-10m" o "40m, 20m"
   - **Potenza W** — per le radio: potenza in watt
   - **Guadagno dBi** — per le antenne: guadagno in dBi
   - **Altezza m** — per le antenne: altezza dal suolo in metri
   - **Note** — note libere
   - **Attivo** — deselezionare per nascondere senza eliminare

3. Fare clic su **"Salva"**

### Utilizzo nel logbook
Una volta aggiunte le antenne, saranno disponibili nel menu a tendina **"Antenna usata"** durante la registrazione di un QSO. Questo permette di vedere le statistiche per antenna nella sezione Report.

---

## 9. Esportazione e importazione

### Esporta ADIF
Scarica il logbook completo in formato **ADIF** (`.adi`), lo standard radioamatoriale universale. Importabile in qualsiasi software di logging (Log4OM, DXKeeper, Ham Radio Deluxe, ecc.).

1. Navigare in **Esporta**
2. Fare clic su **"Scarica ADIF"**

### Esporta CSV
Scarica il logbook in formato **CSV** (foglio di calcolo), compatibile con Microsoft Excel e LibreOffice Calc.

1. Fare clic su **"Scarica CSV"**

> Il file viene esportato con codifica UTF-8 BOM per la corretta visualizzazione delle lettere accentate in Excel.

### Esporta PDF
Genera un documento **PDF in formato A4 orizzontale** con tutti i QSO in tabella, intestazione con il nominativo e piè di pagina con numerazione.

1. Fare clic su **"Scarica PDF"**

### Importa ADIF
Importa un file ADIF esistente nel logbook.

1. Fare clic su **"Scegli file ADIF"**
2. Selezionare il file `.adi` o `.adif`
3. Fare clic su **"Importa"**

L'applicazione mostrerà quanti QSO sono stati importati e quanti saltati (duplicati già presenti).

> **I duplicati vengono rilevati** confrontando nominativo + data + ora. Stessa data/ora con stesso nominativo = QSO già presente, viene saltato.

---

## 10. Impostazioni

### Profilo utente
- **Nome e Cognome** — nome da visualizzare
- **Email** — indirizzo email dell'account

### Credenziali MapForHam
Per abilitare la sincronizzazione con MapForHam:

1. Registrarsi su [mapforham.com](https://www.mapforham.com)
2. Ottenere l'**API key** dalla propria pagina profilo MFH
3. Nella sezione Impostazioni dell'app, inserire:
   - **Username MFH** — il proprio nominativo registrato su MFH
   - **API Key MFH** — la chiave API (verrà salvata in modo sicuro)
4. Fare clic su **"Test connessione MFH"** per verificare

> 💡 Le credenziali sono personali e associate al singolo account. Ogni utente inserisce le proprie credenziali MFH.

### La mia stazione
- **Il mio Gridsquare (QTH)** — il locator della propria stazione (es. `JN70`). Usato come punto centrale della mappa QSO.

### Sincronizzazione automatica
- **Intervallo sync** — ogni quanti minuti il server controlla se ci sono QSO da sincronizzare con MFH (default: 5 minuti)

Fare clic su **"Salva impostazioni"** per confermare le modifiche.

---

## 11. Sincronizzazione con MapForHam

L'applicazione sincronizza automaticamente i QSO con **MapForHam (MFH)**, il portale italiano per radioamatori.

### Come funziona
- Ogni QSO salvato ha uno stato di sincronizzazione:
  - ✓ (spunta verde) = sincronizzato con MFH
  - … (tre puntini) = solo locale, in attesa di sync

- **Al salvataggio**: se l'API key è configurata, il QSO viene sincronizzato immediatamente
- **In background**: ogni N minuti (configurabile), il server sincronizza automaticamente i QSO pendenti
- **Sincronizzazione manuale**: fare clic sul pulsante **"Sincronizza ora"** nella dashboard

### Eliminazione
Quando si elimina un QSO già sincronizzato, viene eliminato anche da MapForHam automaticamente.

### Logbook remoto
La sezione Esporta include anche un pulsante per **leggere il logbook remoto** direttamente da MFH, utile per verificare cosa è stato sincronizzato.

---

## 12. Uso offline e PWA

### Funzionamento offline
L'applicazione è progettata per funzionare anche **senza connessione internet**:

- ✅ Visualizzare il logbook esistente
- ✅ Aggiungere nuovi QSO (vengono salvati localmente)
- ✅ Modificare ed eliminare QSO locali
- ✅ Visualizzare report e mappa (dati già caricati)
- ❌ Sincronizzare con MapForHam (richiede connessione)
- ❌ QRZ Lookup (richiede connessione)

### Coda offline
I QSO aggiunti in modalità offline vengono messi in una **coda**. Il contatore nella barra di navigazione mostra quanti QSO sono in attesa. Quando la connessione torna, vengono sincronizzati automaticamente.

### Installare come app (PWA)

#### Android / Chrome
1. Aprire l'applicazione nel browser Chrome
2. Fare clic sul menu ⋮ → **"Installa app"** o **"Aggiungi a schermata Home"**
3. L'app apparirà come icona sul telefono, funzionando come un'app nativa

#### iPhone / iPad / Safari
1. Aprire l'applicazione in Safari
2. Fare clic su **Condividi** (icona quadrato con freccia)
3. Selezionare **"Aggiungi a schermata Home"**
4. Confermare il nome e fare clic su **"Aggiungi"**

#### Desktop (Chrome / Edge)
1. Nella barra degli indirizzi, fare clic sull'icona di installazione (💻+)
2. Confermare l'installazione

Una volta installata, l'app si apre in modalità schermo intero, senza la barra del browser.

---

## 13. Domande frequenti (FAQ)

**Q: Ho dimenticato la password. Come la recupero?**  
A: Contattare l'amministratore del server. Potrà creare un nuovo account o reimpostare la password tramite il database.

**Q: Posso usare l'app da più dispositivi contemporaneamente?**  
A: Sì. Il database è centralizzato sul server. Puoi usare l'app dal telefono, dal tablet e dal PC contemporaneamente. I dati sono sempre sincronizzati.

**Q: Perché alcuni QSO non appaiono sulla mappa?**  
A: Solo i QSO con il **locator (gridsquare)** del corrispondente vengono visualizzati sulla mappa. Inserire il locator durante la registrazione del QSO, o modificare i QSO esistenti per aggiungere il locator.

**Q: Il QRZ Lookup non trova il nominativo. Perché?**  
A: HamDB.org contiene principalmente nominativi europei e americani. Se il corrispondente non è nel database, i campi non verranno precompilati. Puoi sempre inserirli manualmente.

**Q: Posso condividere il logbook con altri operatori della mia stazione?**  
A: Ogni operatore può creare il proprio account con il proprio nominativo. I dati sono separati per account. Per operazioni multi-operatore (contest, etc.), si consiglia di usare un singolo account condiviso.

**Q: Il formato delle date è corretto per tutti i software ADIF?**  
A: Sì. Il file ADIF esportato usa il formato standard `YYYYMMDD` per le date e `HHMM` per gli orari, compatibile con tutti i software di logging radioamatoriale.

**Q: Quanti QSO posso registrare?**  
A: Non c'è un limite tecnico imposto dall'applicazione. SQLite gestisce senza problemi milioni di record. Le prestazioni dipendono dalla velocità del disco del server.

**Q: I miei dati sono al sicuro?**  
A: I dati sono memorizzati nel database SQLite sul server. Le password sono protette con hashing PBKDF2-SHA256. Si consiglia di configurare backup automatici regolari (vedere la guida all'installazione).

---

*Per assistenza tecnica, contattare IU8VBG.*
