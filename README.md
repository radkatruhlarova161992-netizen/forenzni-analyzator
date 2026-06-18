# Forenzní analyzátor firemních struktur

Streamlit webová aplikace pro shromáždění veřejně dostupných údajů o
českých firmách (ARES, registr DPH, sbírka listin, insolvenční rejstřík)
a nalezení rizikových signálů a propojení osob mezi zadanými firmami.

## Jak spustit ve Visual Studiu

1. Otevři tuto složku jako projekt / nebo jen `app.py` v existujícím
   Python projektu ve Visual Studiu (Python Environments).
2. Nainstaluj závislosti – v terminálu (View → Terminal) spusť:

   ```
   pip install -r requirements.txt
   ```

   V projektu je přiložen i soubor `requirement.txt` kvůli kompatibilitě,
   ale jako hlavní seznam závislostí používej `requirements.txt`.

3. Spusť aplikaci příkazem:

   ```
   streamlit run app.py
   ```

4. Streamlit vypíše lokální adresu, na které aplikace běží.

## Jak appku používat

1. Do textového pole vlož jedno nebo víc IČO (oddělené čárkou nebo
   novým řádkem).
2. Klikni na **Spustit analýzu**.
3. V tabulce uvidíš přehled firem s rizikovými signály. Červeně
   zvýrazněné řádky = likvidace + nespolehlivý plátce DPH současně.
4. Rozbal detail jednotlivé firmy pro osoby (jednatelé/společníci),
   zdroje a odkazy na ruční ověření.
5. Pokud zadáš víc IČO najednou, appka na konci ukáže, jestli se
   nějaká osoba opakuje u víc firem.

## Co appka umí automaticky a co ne

| Zdroj | Stav |
|---|---|
| ARES (základní údaje, stav firmy) | ✅ Plně automatické (reálné REST API) |
| ARES VR (statutární orgány/společníci) | ✅ Automatické, struktura se ale může mezi typy firem lišit |
| Registr DPH – nespolehlivý plátce | ✅ Reálné SOAP volání na ADIS |
| Sbírka listin (Justice.cz) | ⚠️ Pokus o automatické dohledání; pokud nejde, appka dá přímý odkaz pro ruční kontrolu |
| Insolvenční rejstřík (ISIR) | ⚠️ Stejně jako výše – ISIR nemá veřejné bezplatné API pro hromadné dotazy |

Appka nikdy nic nevymýšlí. Když se automatický dotaz nepovede, vždy
uvidíš jasný status ("nutno ověřit ručně") a klikací odkaz na
konkrétní záznam.

## Důležité poznámky

- Všechny rizikové signály jsou popsané neutrálně a vždy se zdrojem.
  Appka sama o sobě nikoho neobviňuje – ukazuje fakta k dalšímu ověření.
- Respektuje limity ARES (nedělej příliš mnoho IČO najednou ve velmi
  krátkém čase).
- Pokud justice.cz nebo isir.justice.cz změní strukturu webu, scraping
  část se může rozbít – v tom případě appka spadne zpátky na fallback
  odkaz, nikdy ne na chybu celé aplikace.

## Deploy na Render

Projekt je připravený pro nasazení jako **Render Python Web Service** bez
dalších ručních úprav.

### 1. Vytvoření GitHub repozitáře

1. V GitHubu vytvoř nový repository.
2. Nahraj do něj celý obsah projektu včetně:
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - `.streamlit/config.toml`
3. Pushni hlavní branch na GitHub.

### 2. Vytvoření Render Web Service

1. Přihlas se do [Render](https://render.com/).
2. Klikni na **New +** → **Web Service**.
3. Zvol **Build and deploy from a Git repository**.
4. Propoj Render s GitHubem, pokud ještě není propojený.
5. Vyber repository s touto aplikací.

### 3. Konfigurace nasazení

Pokud Render načte `render.yaml`, služba se předvyplní automaticky:

- **Name:** `forensic-company-analyzer`
- **Runtime:** `Python`
- **Plan:** `Free`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

Není potřeba ručně nastavovat pevný port ani localhost.

### 4. Automatické nasazení

1. Potvrď vytvoření služby.
2. Render provede build a první deploy automaticky.
3. Po dokončení dostane aplikace veřejnou URL.
4. Každý další push do propojeného GitHub repozitáře spustí automatický deploy.

### 5. Poznámka k souborům pro Render

- `render.yaml` obsahuje build a start konfiguraci.
- `.streamlit/config.toml` zapíná headless režim vhodný pro server.
- Aplikace používá port z proměnné prostředí `PORT`, takže je kompatibilní s Render Web Service.
