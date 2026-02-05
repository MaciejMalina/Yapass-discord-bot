# Discord Event & Infrastructure Manager (RPi 4B)

Profesjonalny system automatyzacji grupy Discord zintegrowany z **Google Calendar API**, oferujący zaawansowane funkcje zarządzania harmonogramem oraz monitoring infrastruktury Raspberry Pi w czasie rzeczywistym.


## Kluczowe Funkcjonalności

### Zarządzanie Harmonogramem (Google API)
- **Integracja Google Calendar v3**: Automatyczne tworzenie i usuwanie wydarzeń bezpośrednio z poziomu Discorda.
- **Inteligentne Przypomnienia**: System raportowania porannego (08:00) z precyzyjnym pingowaniem uczestników (Attendee Tracking) zapisanych za pomocą reakcji ✅.
- **Geocoding & Weather**: Integracja z **Nominatim API** (OSM) oraz **Open-Meteo**, dostarczająca prognozę pogody dla konkretnych lokalizacji wydarzeń.

### System Zarządzania Zadaniami (TODO)
- **Persystencja Danych**: Wykorzystanie relacyjnej bazy danych **SQLite** do zarządzania listami zadań grupowych.
- **Dashboard Podglądu**: Wizualizacja stanu list TODO w czasie rzeczywistym na panelu webowym.

### Monitoring Infrastruktury (SRE)
- **Web Dashboard (Quart)**: Asynchroniczny panel telemetrii monitorujący obciążenie CPU, RAM oraz temperaturę SoC Raspberry Pi.
- **Healthcheck & Alerty**: Skrypt monitorujący stan kontenerów Docker oraz temperaturę procesora, wysyłający krytyczne powiadomienia via **Discord Webhooks**.
- **Wizualizacja Danych**: Wykorzystanie **Chart.js** do prezentacji trendów temperaturowych urządzenia.

## tack Technologiczny

- **Język**: Python 3.11 (Asyncio, Discord.py)
- **Web**: Quart (Asynchroniczny framework webowy), HTML5/CSS3, Chart.js
- **DevOps**: Docker & Docker Compose (Architektura ARMv8)
- **Baza Danych**: SQLite3
- **Monitoring**: Bash Scripting, Cron, Linux SysFS

## Szybki Start

### Wymagania
- Raspberry Pi 4B (lub dowolny host Linux z Dockerem)
- Konto Google Cloud (z aktywnym Calendar API)
- Token bota Discord

### Instalacja
1. Sklonuj repozytorium:
   ```bash
   git clone [https://github.com/MaciejMalina/Yapass-discord-bot.git](https://github.com/MaciejMalina/Yapass-discord-bot.git)
   cd Yapass-discord-bot```

2. Skonfiguruj środowisko o odpowiednie tokeny/pliki:
- .env
- credentials.json 

3. Uruhchom system: 
- docker-compose up -d --build
