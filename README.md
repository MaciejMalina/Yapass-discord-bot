# Yapass Discord Manager (v2.7)
Zaawansowany system automatyzacji grupy Discord, hostowany na Raspberry Pi 4B. Projekt łączy w sobie zarządzanie czasem (Google API), finanse grupowe oraz monitoring infrastruktury SRE w czasie rzeczywistym.

---

## Architektura i Technologie
Projekt wykorzystuje architekturę modularną opartą na Cogs, co pozwala na pełną izolację logiki biznesowej poszczególnych modułów.

* **Backend:** Python 3.11 (Asyncio)
* **Framework:** Discord.py + Quart (Asynchroniczny Dashboard)
* **Integracje:** Google Calendar API v3, Open-Meteo API, Nominatim Geocoding
* **Konteneryzacja:** Docker & Docker Compose dla architektury ARM (Raspberry Pi)

---

## Kluczowe Moduły (Cogs)

### Harmonogram i Pogoda
Zaawansowana synchronizacja z kalendarzem Google.

* **Inteligentne Raporty:** Codziennie o 9:00 bot analizuje wydarzenia. Jeśli kalendarz jest pusty, bot nie wysyła zbędnych powiadomień (Anti-Spam).
* **Rich Embeds:** Powiadomienia zawierają nazwę, precyzyjną godzinę, lokalizację oraz prognozę pogody wygenerowaną na podstawie współrzędnych GPS wydarzenia.
* **Zliczanie obecności:** System śledzenia reakcji ✅, który w raporcie porannym listuje wszystkich potwierdzonych uczestników.

### Finance & Debt Tracker
System rozliczeń grupowych z dynamicznym podziałem kosztów.

* **Selective Member Filtering:** Bot filtruje listę użytkowników, pokazując w menu tylko osoby mające dostęp do danego kanału tekstowego.
* **Social Billing:** Automatyczny podział kwoty (np. za pizzę) na N wybranych osób + płatnika.
* **System CRUD:** Pełne zarządzanie długami przez komendy `/rozlicz`, `/moje_dlugi` oraz `/oddalem`.

### Modularny System TODO
* Tworzenie dedykowanych list zadań (zakupy, projekty, praca).
* Pełna persystencja danych – zadania nie znikają po restarcie bota.

### Monitoring Systemowy (SRE)
* **Komenda `/status`:** Wyświetla aktualne zużycie CPU, RAM oraz Uptime bota.
* **Web Dashboard:** Panel www dostępny w sieci lokalnej (port 5000), wyświetlający metryki życiowe Malinki.

## Instalacja i Deployment
1. Klonowanie i Środowisko
`git clone https://github.com/MaciejMalina/Yapass-discord-bot.git cd Yapass-discord-bot`

2. Konfiguracja .env
Utwórz plik `.env` i uzupełnij dane: DISCORD_TOKEN=twoj_token_bota CALENDAR_ID=twoj_id_kalendarza

3. Uruchomienie (Docker)
docker-compose up -d --build
