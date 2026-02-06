import discord
from discord.ext import commands
import os
import psutil
import logging
import asyncio
import sqlite3
from quart import Quart, render_template_string
from dotenv import load_dotenv
from datetime import datetime, timedelta
from database import DatabaseManager
from logging.handlers import RotatingFileHandler

load_dotenv()
db = DatabaseManager()
temp_history = []

# --- KONFIGURACJA LOGERA ---
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler = RotatingFileHandler('bot.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

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
            --bg: #0b0e14; --card: #161b22; --accent: #58a6ff; 
            --text: #c9d1d9; --border: #30363d; --todo-bg: #1c2128;
            --success: #238636; --warning: #d29922;
        }
        body { 
            font-family: 'Outfit', sans-serif; background: var(--bg); 
            color: var(--text); margin: 0; padding: 20px; line-height: 1.5;
        }
        .container { max-width: 1200px; margin: auto; }
        header { 
            display: flex; justify-content: space-between; align-items: center; 
            border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 30px;
        }
        .status-badge { 
            background: var(--success); color: white; padding: 6px 16px; 
            border-radius: 20px; font-size: 0.85rem; font-weight: 600;
        }
        .grid-stats { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }
        .card { 
            background: var(--card); border: 1px solid var(--border); 
            padding: 20px; border-radius: 12px;
        }
        .card-chart { grid-column: 1 / -1; min-height: 350px; }
        .label { color: #8b949e; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .value { font-size: 2rem; font-weight: 600; color: var(--accent); }
        .unit { font-size: 1rem; color: #8b949e; }
        h2 { border-left: 4px solid var(--accent); padding-left: 15px; margin: 40px 0 20px; font-size: 1.4rem; }
        .todo-grid { 
            display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
            gap: 20px; margin-bottom: 40px; 
        }
        .todo-card { 
            background: var(--todo-bg); border: 1px solid var(--border);
            border-top: 4px solid var(--accent); padding: 20px; border-radius: 8px; 
        }
        .todo-title { font-weight: 600; color: var(--accent); margin-bottom: 15px; font-size: 1.1rem; }
        .todo-list { list-style: none; padding: 0; margin: 0; }
        .todo-item { padding: 8px 0; border-bottom: 1px solid #30363d55; display: flex; justify-content: space-between; }
        .logs-container { 
            background: #010409; border: 1px solid var(--border); border-radius: 12px; 
            padding: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; 
            max-height: 400px; overflow-y: auto;
        }
        .log-entry { padding: 4px 0; border-bottom: 1px solid #161b22; color: #8b949e; }
        footer { margin-top: 60px; padding: 20px; border-top: 1px solid var(--border); text-align: center; color: #484f58; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1 style="margin:0;">Yapass Command Center</h1>
                <p style="color: #8b949e; margin:5px 0;">Raspberry Pi 4B Monitoring | v2.5</p>
            </div>
            <div class="status-badge">● SYSTEM ONLINE</div>
        </header>

        <div class="grid-stats">
            <div class="card"><div class="label">Obciążenie CPU</div><div class="value">{{ cpu }}<span class="unit">%</span></div></div>
            <div class="card"><div class="label">Pamięć RAM</div><div class="value">{{ ram }}<span class="unit">%</span></div></div>
            <div class="card"><div class="label">Temperatura SoC</div><div class="value" style="color:var(--warning)">{{ temp }}<span class="unit">°C</span></div></div>
            <div class="card"><div class="label">System Uptime</div><div class="value" style="font-size: 1.2rem;">{{ uptime }}</div></div>
            
            <div class="card card-chart">
                <div class="label">Telemetria Temperatury (Live)</div>
                <div style="height: 300px;"><canvas id="tempChart"></canvas></div>
            </div>
        </div>

        <h2>📋 Aktywne Listy TODO</h2>
        <div class="todo-grid">
            {% for category, items in todo_data.items() %}
            <div class="todo-card">
                <div class="todo-title">{{ category | upper }}</div>
                <ul class="todo-list">
                    {% for item in items %}<li class="todo-item"><span>{{ item.text }}</span><span style="color:#8b949e; font-size:0.8rem">@{{ item.user }}</span></li>{% endfor %}
                </ul>
            </div>
            {% endfor %}
        </div>

        <h2>📝 Logi Systemowe</h2>
        <div class="logs-container">
            {% for log in logs %}<div class="log-entry">{{ log }}</div>{% endfor %}
        </div>

        <footer>Ostatnia aktualizacja: {{ now }} | Monitoring Port: 5000</footer>
    </div>

    <script>
        const ctx = document.getElementById('tempChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: {{ labels | tojson }},
                datasets: [{
                    label: 'Temperatura CPU (°C)',
                    data: {{ values | tojson }},
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { grid: { color: '#30363d' }, ticks: { color: '#8b949e' } },
                    x: { grid: { display: false }, ticks: { color: '#8b949e' } }
                }
            }
        });
        setTimeout(() => location.reload(), 10000);
    </script>
</body>
</html>
"""

@app.route('/')
async def index():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f: t = float(f.read()) / 1000
    except: t = 0.0
    
    now_time = datetime.now().strftime("%H:%M:%S")
    temp_history.append({"time": now_time, "value": t})
    if len(temp_history) > 20: temp_history.pop(0)

    conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
    c.execute("SELECT category, item, user FROM todo ORDER BY category ASC")
    todo_rows = c.fetchall(); conn.close()
    todo_data = {}
    for cat, text, user in todo_rows:
        if cat not in todo_data: todo_data[cat] = []
        todo_data[cat].append({'text': text, 'user': user})

    try:
        with open("bot.log", "r", encoding='utf-8') as f: logs = f.readlines()[-25:]; logs.reverse()
    except: logs = ["Brak logów."]

    uptime = str(timedelta(seconds=int(datetime.now().timestamp() - psutil.boot_time())))
    return await render_template_string(DASHBOARD_HTML, cpu=cpu, ram=ram, temp=t, 
                                        labels=[h["time"] for h in temp_history], 
                                        values=[h["value"] for h in temp_history],
                                        todo_data=todo_data, logs=logs, now=now_time, uptime=uptime)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True; intents.members = True; intents.reactions = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        self.loop.create_task(app.run_task(host='0.0.0.0', port=5000))
        await self.tree.sync()

bot = MyBot()
bot.run(os.getenv('DISCORD_TOKEN'))