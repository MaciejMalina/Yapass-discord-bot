# Yapass Discord Manager (RPi 4B)

System automatyzacji grupy Discord hostowany na **Raspberry Pi 4B**, integrujący narzędzia do zarządzania zadaniami (TODO) oraz harmonogramem (Google Calendar).

## Kluczowe Funkcjonalności
- **Integracja Google Calendar API**: Automatyczne zarządzanie wydarzeniami z wykrywaniem kolizji.
- **Daily Stand-up**: System porannych raportów (08:00) z inteligentnym pingowaniem uczestników (Attendee Tracking) zapisanych przez reakcje ✅.
- **Geocoding & Weather**: Automatyczne pobieranie pogody dla lokalizacji wydarzeń (Open-Meteo & Nominatim API).
- **Web Dashboard**: Monitoring parametrów sprzętowych Malinki (CPU, RAM, Temp) w czasie rzeczywistym (Quart).
- **Persystencja danych**: Zarządzanie stanem list TODO i uczestników w relacyjnej bazie **SQLite**.

## tack Technologiczny
- **Backend**: Python 3.11 (discord.py, asyncio)
- **Web**: Quart (Asynchroniczny Flask)
- **Infrastructure**: Docker & Docker Compose
- **Database**: SQLite

## Szybki Start (Deployment)

1. Sklonuj repozytorium:
   ```bash
   git clone [https://github.com/MaciejMalina/Yapass-discord-bot.git](https://github.com/MaciejMalina/Yapass-discord-bot.git)
   cd Yapass-discord-bot ```

2. Przygotuj pliki konfiguracyjne:
   ```pliki .env oraz credentials.json```

3. Uruchom kontener:
   ```docker-compose up -d --build```
