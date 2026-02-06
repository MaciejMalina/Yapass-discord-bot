#!/bin/bash

# Konfiguracja
THRESHOLD=70
WEBHOOK_URL="https://discord.com/api/webhooks/1467203227236696145/RiHAh2GxHtd6jupxu0IXI7p9QKayveTo2CXan5f8OsR-mm6DfHz45zP26K4RsYpyT9zj"
TEMP=$(vcgencmd measure_temp | egrep -o '[0-9]*\.[0-9]*')

# 1. Sprawdź temperaturę
if (( $(echo "$TEMP > $THRESHOLD" | bc -l) )); then
    curl -H "Content-Type: application/json" -X POST -d "{\"content\": \"**ALERT TEMP**: Malinka się grzeje! Obecnie: ${TEMP}°C\"}" $WEBHOOK_URL
fi

# 2. Sprawdź czy kontener Dockera działa
if [ ! "$(docker ps -q -f name=calendar_bot)" ]; then
    curl -H "Content-Type: application/json" -X POST -d "{\"content\": \"**CRITICAL**: Kontener bota padł! Próbuję zrestartować...\"}" $WEBHOOK_URL
    docker-compose restart bot
fi
