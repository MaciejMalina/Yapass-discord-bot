# Yapass Discord Manager (RPi 4B)

Profesjonalny, modularny system automatyzacji grupy Discord hostowany na **Raspberry Pi 4B**. Projekt łączy zarządzanie czasem, wydatkami oraz monitoring infrastruktury w czasie rzeczywistym.

## Kluczowe Moduły (Cogs)

### Harmonogram i Kalendarz (Google API)
- **Synchronizacja z Google Calendar v3**: Dodawanie i usuwanie wydarzeń z obsługą kolizji czasowych.
- **Daily Stand-up (09:00)**: Poranne raporty z listą obecności osób zapisanych przez reakcję ✅.
- **Geocoding & Weather**: Automatyczna prognoza pogody dla lokalizacji eventu (Open-Meteo & Nominatim API).

### Moduł Finansowy (Grupowe Rozliczenia)
- **Zarządzanie Wydatkami**: Rejestrowanie wspólnych kosztów grupy w bazie SQLite.
- **Automatyczne Bilansowanie**: Szybki podgląd salda wydatków dla każdego członka grupy.

### System TODO
- **Modularne Listy**: Zarządzanie wieloma listami zadań jednocześnie.
- **Persystencja**: Pełne przechowywanie stanu zadań nawet po restarcie bota.

### Monitoring i SRE (Observability)
- **Web Dashboard**: Asynchroniczny panel (Quart) wyświetlający obciążenie CPU, RAM oraz temperaturę SoC.
- **Telemetria Live**: Dynamiczny wykres temperatury historycznej przy użyciu Chart.js.
- **Self-healing Script**: Skrypt `healthcheck.sh` monitorujący stan kontenera Docker i temperaturę procesora.

## Stack Technologiczny
- **Backend**: Python 3.11 (Asyncio, Discord.py, Quart)
- **Infrastruktura**: Docker & Docker Compose (ARMv8)
- **Baza Danych**: SQLite3 (Z rotacją logów)
- **Frontend**: HTML5, CSS3, JavaScript (Chart.js)

## Wdrożenie (Deployment)

1. **Konfiguracja**:
   - Skopiuj `.env.example` -> `.env` i podaj tokeny.
   - Umieść `credentials.json` w folderze głównym.
2. **Budujemy projekt w dockerze**:
	`docker-compose up -d --build`
3. **Healthcheck**:
   - Dodaj skrypt do `crontab -e`: `*/15 * * * * /sciezka/do/projektu/healthcheck.sh`

#Projekt Maciej Malina - 2026 
