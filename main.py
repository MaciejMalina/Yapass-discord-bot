import discord
from discord import app_commands
from discord.ext import tasks
import os
import requests
import sqlite3
import psutil
import logging
import asyncio
from quart import Quart, render_template_string
from dotenv import load_dotenv
import dateparser
from datetime import datetime, timedelta, timezone
from calendar_utils import add_event, get_calendar_service

# Załadowanie zmiennych środowiskowych
load_dotenv()

# --- KONFIGURACJA LOGERA ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s', 
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord_bot')

# --- BAZA DANYCH ---
def init_db():
    """Inicjalizacja bazy danych SQLite dla systemu TODO."""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS todo 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  category TEXT, 
                  item TEXT, 
                  user TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS participants 
             (message_id INTEGER, user_id INTEGER, username TEXT, 
              event_name TEXT, event_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sent_reminders 
             (event_id TEXT, sent_date TEXT)''')
    conn.commit()
    conn.close()
    logger.info("Baza danych została zainicjalizowana.")

init_db()

# --- DASHBOARD UI (QUART) ---
app = Quart(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yapass Command Center</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono&family=Outfit:wght@300;600&display=swap" rel="stylesheet">
    <style>
        :root { 
            --bg: #0b0e14; 
            --card: #161b22; 
            --accent: #58a6ff; 
            --text: #c9d1d9; 
            --border: #30363d; 
            --todo-bg: #1c2128; 
        }
        body { 
            font-family: 'Outfit', sans-serif; 
            background: var(--bg); 
            color: var(--text); 
            margin: 0; 
            padding: 20px; 
        }
        .container { max-width: 1100px; margin: auto; }
        
        header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-bottom: 1px solid var(--border); 
            padding-bottom: 20px; 
        }
        .status-badge { 
            background: #238636; 
            color: white; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-size: 0.85rem; 
        }

        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
            gap: 20px; 
            margin: 25px 0; 
        }
        .card { 
            background: var(--card); 
            border: 1px solid var(--border); 
            padding: 20px; 
            border-radius: 12px; 
        }
        .label { color: #8b949e; font-size: 0.9rem; margin-bottom: 10px; }
        .value { font-size: 1.8rem; font-weight: 600; color: var(--accent); }

        /* TODO Section */
        .todo-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 40px; 
        }
        .todo-card { 
            background: var(--todo-bg); 
            border-left: 4px solid var(--accent); 
            padding: 15px; 
            border-radius: 8px; 
            border: 1px solid var(--border); 
        }
        .todo-title { 
            font-weight: 600; 
            text-transform: uppercase; 
            color: var(--accent); 
            margin-bottom: 12px; 
            border-bottom: 1px solid var(--border); 
            padding-bottom: 5px;
        }
        .todo-list { list-style: none; padding: 0; margin: 0; }
        .todo-item { 
            padding: 6px 0; 
            border-bottom: 1px solid #30363d33; 
            font-size: 0.95rem; 
        }
        .todo-user { color: #8b949e; font-size: 0.8rem; font-style: italic; }

        .logs-container { 
            background: #010409; 
            border: 1px solid var(--border); 
            border-radius: 12px; 
            padding: 20px; 
            font-family: 'JetBrains Mono', monospace; 
            font-size: 0.85rem; 
            height: 350px; 
            overflow-y: auto; 
        }
        .log-entry { border-bottom: 1px solid #161b22; padding: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1 style="margin:0;">Yapass Command Center</h1>
                <p style="color: #8b949e; margin:5px 0;">Host: Raspberry Pi 4B | Port: 5000</p>
            </div>
            <div class="status-badge">● ONLINE</div>
        </header>

        <div class="grid">
            <div class="card"><div class="label">CPU LOAD</div><div class="value">{{ cpu }}%</div></div>
            <div class="card"><div class="label">RAM USAGE</div><div class="value">{{ ram }}%</div></div>
            <div class="card"><div class="label">TEMPERATURE</div><div class="value" style="color:#d29922">{{ temp }}°C</div></div>
            <div class="card"><div class="label">UPTIME</div><div class="value" style="font-size: 1.1rem;">{{ uptime }}</div></div>
        </div>

        <h2 style="border-left: 4px solid var(--accent); padding-left: 15px;">📋 Listy TODO (Podgląd)</h2>
        <div class="todo-grid">
            {% for category, items in todo_data.items() %}
            <div class="todo-card">
                <div class="todo-title">{{ category }}</div>
                <ul class="todo-list">
                    {% for item in items %}
                    <li class="todo-item">
                        {{ item.text }} <span class="todo-user">(@{{ item.user }})</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endfor %}
        </div>

        <h2 style="border-left: 4px solid var(--accent); padding-left: 15px;">📝 Logi Systemowe</h2>
        <div class="logs-container">
            {% for log in logs %}
                <div class="log-entry">{{ log }}</div>
            {% endfor %}
        </div>

        <div class="card" style="grid-column: span 2;">
            <canvas id="tempChart"></canvas>
        </div>

        <footer style="margin-top: 40px; font-size: 0.8rem; text-align: center; color: #484f58;">
            Ostatnia aktualizacja: {{ now }} | Auto-refresh co 10s
        </footer>
    </div>
    <script>setTimeout(function(){ location.reload(); }, 10000);</script>
    <script>
        const ctx = document.getElementById('tempChart').getContext('2d');
        const tempChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['12:00', '12:15', '12:30', '12:45', '13:00'], // Przykładowe dane
                datasets: [{
                    label: 'Temperatura CPU (°C)',
                    data: [45, 48, 52, 49, 50], // Przykładowe dane
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: false, grid: { color: '#30363d' } },
                    x: { grid: { color: '#30363d' } }
                },
                plugins: {
                    legend: { labels: { color: '#c9d1d9' } }
                }
            }
        });

        // Twoja stara funkcja przeładowania strony może zostać pod spodem:
        setTimeout(function(){ location.reload(); }, 60000);
    </script>
</body>
</html>
"""

@app.route('/')
async def index():
    """Obsługa dashboardu webowego."""
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = f"{int(f.read()) / 1000:.1f}"
    except: temp = "0.0"
    
    todo_data = {}
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT category, item, user FROM todo ORDER BY category ASC")
    rows = c.fetchall()
    conn.close()

    for cat, text, user in rows:
        if cat not in todo_data:
            todo_data[cat] = []
        todo_data[cat].append({'text': text, 'user': user})

    try:
        with open("bot.log", "r", encoding='utf-8') as f:
            logs = f.readlines()[-25:]
            logs.reverse()
    except: logs = ["Brak logów lub problem z plikiem."]

    uptime = str(timedelta(seconds=int(datetime.now().timestamp() - psutil.boot_time())))
    
    return await render_template_string(
        DASHBOARD_HTML, 
        cpu=cpu, ram=ram, temp=temp, uptime=uptime,
        todo_data=todo_data,
        logs=logs, now=datetime.now().strftime("%H:%M:%S")
    )

# --- UI: LISTA WYDARZEŃ I USUWANIE ---

class EventDeleteSelect(discord.ui.Select):
    """Rozwijane menu do wyboru wydarzenia do usunięcia."""
    def __init__(self, options):
        super().__init__(
            placeholder="Wybierz wydarzenie, które chcesz usunąć...",
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        service = get_calendar_service()
        try:
            service.events().delete(
                calendarId=os.getenv('CALENDAR_ID'), 
                eventId=self.values[0]
            ).execute()
            await interaction.response.send_message(f"🗑️ Pomyślnie usunięto wydarzenie z Kalendarza Google.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd podczas usuwania: {e}", ephemeral=True)

class CalendarView(discord.ui.View):
    """Widok paginacji z menu wyboru (Select Menu)."""
    def __init__(self, events, current_page=0):
        super().__init__(timeout=120)
        self.events = events
        self.page = current_page
        self.per_page = 3
        
        start = self.page * self.per_page
        page_events = self.events[start : start + self.per_page]
        
        if page_events:
            options = [
                discord.SelectOption(
                    label=e['summary'][:25], 
                    value=e['id'], 
                    description=f"Dnia: {e['start'].get('dateTime', 'Brak')[:10]}"
                ) for e in page_events
            ]
            self.add_item(EventDeleteSelect(options))

    @discord.ui.button(label="Poprzednia strona", style=discord.ButtonStyle.gray, emoji="◀️")
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_view(interaction)

    @discord.ui.button(label="Następna strona", style=discord.ButtonStyle.gray, emoji="▶️")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.per_page < len(self.events):
            self.page += 1
            await self.update_view(interaction)

    async def update_view(self, interaction):
        new_view = CalendarView(self.events, self.page)
        await interaction.response.edit_message(embed=new_view.create_embed(), view=new_view)

    def create_embed(self):
        embed = discord.Embed(title="🗓️ Nadchodzące wydarzenia", color=discord.Color.blue())
        start = self.page * self.per_page
        for event in self.events[start : start + self.per_page]:
            st = event['start'].get('dateTime', event['start'].get('date'))
            dt = dateparser.parse(st)
            loc = event.get('location', 'Brak lokalizacji')
            
            desc = event.get('description', '')
            weather_line = next((line for line in desc.split('\n') if "🌡️" in line), "Brak danych o pogodzie.")
            
            embed.add_field(
                name=event['summary'], 
                value=f"🕒 **{dt.strftime('%d.%m %H:%M')}**\n📍 {loc}\n{weather_line}", 
                inline=False
            )
        embed.set_footer(text=f"Strona {self.page + 1} | Wybierz z menu poniżej, aby usunąć konkretny event.")
        return embed

# --- KLASA BOTA ---

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.daily_report.start()
        self.loop.create_task(app.run_task(host='0.0.0.0', port=5000))
        await self.tree.sync()
        logger.info("Bot zalogowany i zsynchronizowany.")

    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) == "✅" and payload.user_id != self.user.id:
            conn = sqlite3.connect('bot_data.db')
            c = conn.cursor()
            channel = self.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if message.embeds:
                embed = message.embeds[0]
                event_name = embed.title
                c.execute("INSERT INTO participants (message_id, user_id, username, event_name) VALUES (?, ?, ?, ?)",
                          (payload.message_id, payload.user_id, str(payload.member), event_name))
                conn.commit()
            conn.close()

    async def on_raw_reaction_remove(self, payload):
        if str(payload.emoji) == "✅":
            conn = sqlite3.connect('bot_data.db')
            c = conn.cursor()
            c.execute("DELETE FROM participants WHERE message_id = ? AND user_id = ?", 
                      (payload.message_id, payload.user_id))
            conn.commit()
            conn.close()

    @tasks.loop(minutes=1)
    async def daily_report(self):
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            logger.info("Generowanie porannego raportu...")
            channel = self.get_channel(1468962094438158504)
            if not channel: return

            service = get_calendar_service()
            today_start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            today_end = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

            try:
                events = service.events().list(
                    calendarId=os.getenv('CALENDAR_ID'), 
                    timeMin=today_start, timeMax=today_end, 
                    singleEvents=True, orderBy='startTime'
                ).execute().get('items', [])

                if not events:
                    await channel.send("☕ **Dzień dobry!** Dzisiaj nie ma żadnych zaplanowanych wydarzeń.")
                    return

                await channel.send("🌅 **PORANNY RAPORT WYDARZEŃ NA DZIŚ**")

                conn = sqlite3.connect('bot_data.db')
                c = conn.cursor()
                today_str = now.strftime('%Y-%m-%d')

                for ev in events:
                    event_id = ev['id']
                    c.execute("SELECT 1 FROM sent_reminders WHERE event_id = ? AND sent_date = ?", (event_id, today_str))
                    if c.fetchone(): continue

                    c.execute("SELECT user_id FROM participants WHERE event_name = ?", (ev['summary'],))
                    attendees = c.fetchall()
                    
                    pings = " ".join([f"<@{a[0]}>" for a in attendees]) if attendees else "_Brak zapisanych osób_"
                    start_time = dateparser.parse(ev['start'].get('dateTime', ev['start'].get('date')))

                    embed = discord.Embed(title=f"🔔 {ev['summary']}", color=discord.Color.gold())
                    embed.add_field(name="Start", value=start_time.strftime('%H:%M'), inline=True)
                    embed.add_field(name="Ekipa", value=pings, inline=False)
                    
                    await channel.send(embed=embed)

                    c.execute("INSERT INTO sent_reminders (event_id, sent_date) VALUES (?, ?)", (event_id, today_str))
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Błąd raportu: {e}")

# --- POMOCNICZE FUNKCJE (POGODA/LOKALIZACJA) ---

async def get_coordinates(location_text):
    if not location_text or location_text == "Brak":
        return 49.84, 19.79 # Domyślnie Sułkowice
    
    url = f"https://nominatim.openstreetmap.org/search?q={location_text}&format=json&limit=1"
    headers = {'User-Agent': 'DiscordBotGeocoding/1.0'}
    try:
        r = requests.get(url, headers=headers).json()
        if r: return float(r[0]['lat']), float(r[0]['lon'])
    except: pass
    return 49.84, 19.79

async def get_weather(dt, location_text):
    lat, lon = await get_coordinates(location_text)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability&start_date={dt.date()}&end_date={dt.date()}"
    try:
        r = requests.get(url).json()
        hour = dt.hour
        temp = r['hourly']['temperature_2m'][hour]
        rain = r['hourly']['precipitation_probability'][hour]
        return f"🌡️ {temp}°C, Opady: {rain}% (Lokalizacja: {lat:.2f}, {lon:.2f})"
    except:
        return "🌡️ Pogoda: Brak danych."

bot = MyBot()

# --- KOMENDY SLASH ---

@bot.tree.command(name="status", description="Sprawdź stan bota i Raspberry Pi")
async def status_cmd(interaction: discord.Interaction):
    logger.info(f"Komenda /status użyta przez {interaction.user}")
    embed = discord.Embed(title="🚀 System Status", color=discord.Color.blue())
    embed.add_field(name="Dashboard Web", value="`http://IP_MALINY:5000`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kalendarz", description="Dodaj wydarzenie do wspólnego kalendarza")
@app_commands.describe(
    tytul="Czego dotyczy wydarzenie?",
    kiedy="np. 'jutro 20:00', 'sobota 12:00'",
    ile_godzin="Czas trwania (domyślnie 1.0)",
    miejsce="Wpisz np. 'Sułkowice' lub 'Kraków Rynek'"
)
async def kalendarz(interaction: discord.Interaction, tytul: str, kiedy: str, ile_godzin: float = 1.0, miejsce: str = "Brak"):
    await interaction.response.defer()

    dt_start = dateparser.parse(kiedy, settings={'PREFER_DATES_FROM': 'future'})
    if not dt_start:
        await interaction.followup.send("❌ Nie zrozumiałem podanej daty!")
        return
    
    dt_end = dt_start + timedelta(hours=ile_godzin)
    service = get_calendar_service()
    
    try:
        conflicts = service.events().list(
            calendarId=os.getenv('CALENDAR_ID'), 
            timeMin=dt_start.isoformat() + "Z", 
            timeMax=dt_end.isoformat() + "Z", 
            singleEvents=True
        ).execute().get('items', [])
        
        if conflicts:
            await interaction.followup.send(f"⚠️ Kolizja! W tym czasie trwa już: **{conflicts[0]['summary']}**.")
            return

        weather_info = await get_weather(dt_start, miejsce)
        description = f"Dodane przez: {interaction.user.display_name}\n{weather_info}"
        
        event_link = add_event(tytul, dt_start.isoformat(), dt_end.isoformat(), description, miejsce)
        
        embed = discord.Embed(title=f"📅 {tytul}", url=event_link, color=discord.Color.green())
        embed.add_field(name="Kiedy", value=dt_start.strftime('%d.%m %H:%M'), inline=True)
        embed.add_field(name="Miejsce", value=miejsce, inline=True)
        embed.add_field(name="Pogoda", value=weather_info, inline=False)
        embed.set_footer(text="Zaznacz reakcję: ✅ (Będę), ❌ (Brak), ❓ (Może)")
        
        message = await interaction.followup.send(embed=embed)
        for emoji in ["✅", "❌", "❓"]:
            await message.add_reaction(emoji)
            
    except Exception as e:
        logger.error(f"Błąd /kalendarz: {e}")
        await interaction.followup.send(f"❌ Błąd podczas dodawania do kalendarza: {e}")

@bot.tree.command(name="lista", description="Pokaż nadchodzące wydarzenia")
async def lista(interaction: discord.Interaction):
    service = get_calendar_service()
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    try:
        events = service.events().list(
            calendarId=os.getenv('CALENDAR_ID'), 
            timeMin=now, 
            singleEvents=True, 
            orderBy='startTime'
        ).execute().get('items', [])
        
        if not events:
            await interaction.response.send_message("Aktualnie brak zaplanowanych wydarzeń.")
            return

        view = CalendarView(events)
        await interaction.response.send_message(embed=view.create_embed(), view=view)
    except Exception as e:
        await interaction.response.send_message(f"❌ Nie udało się pobrać listy: {e}")

# --- KOMENDY TODO ---

@bot.tree.command(name="todo_wszystkie", description="Wyświetla absolutnie wszystkie listy TODO i ich zawartość")
async def todo_all(interaction: discord.Interaction):
    logger.info(f"Użytkownik {interaction.user} sprawdza wszystkie listy TODO.")
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT category, item, user FROM todo ORDER BY category ASC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await interaction.response.send_message("📭 Wszystkie listy są aktualnie puste.")
        return

    todo_map = {}
    for cat, item, user in rows:
        if cat not in todo_map:
            todo_map[cat] = []
        todo_map[cat].append(f"• {item} `(od: {user})`")

    embed = discord.Embed(
        title="📋 Zbiorcze zestawienie wszystkich list TODO",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )

    for category, items in todo_map.items():
        content = "\n".join(items)
        if len(content) > 1024:
            content = content[:1021] + "..."
        
        embed.add_field(
            name=f"🗂️ Lista: {category.upper()}",
            value=content,
            inline=False
        )

    embed.set_footer(text="Pełny podgląd graficzny dostępny na Dashboardzie port:5000")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="todo_dodaj", description="Dodaj przedmiot do listy grupowej")
async def todo_add(interaction: discord.Interaction, lista: str, rzecz: str):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO todo (category, item, user) VALUES (?, ?, ?)", 
              (lista.lower(), rzecz, interaction.user.display_name))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"➕ Dodano **{rzecz}** do listy **{lista}**!")

@bot.tree.command(name="todo_pokaz", description="Wyświetl zawartość listy")
async def todo_show(interaction: discord.Interaction, lista: str):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT item, user FROM todo WHERE category = ?", (lista.lower(),))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await interaction.response.send_message(f"Lista **{lista}** jest pusta.")
        return
    
    items = "\n".join([f"• {r[0]} (od: {r[1]})" for r in rows])
    embed = discord.Embed(title=f"📋 Lista: {lista}", description=items, color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="todo_wyczysc", description="Usuń całą listę")
async def todo_clear(interaction: discord.Interaction, lista: str):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM todo WHERE category = ?", (lista.lower(),))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"🧹 Lista **{lista}** została wyczyszczona.")

# --- URUCHOMIENIE ---
bot.run(os.getenv('DISCORD_TOKEN'))