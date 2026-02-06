import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import sqlite3
import dateparser
import requests
from datetime import datetime, timedelta, timezone
from calendar_utils import add_event, get_calendar_service

class Calendar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_report.start()

    async def get_coordinates(self, location_text):
        if not location_text or location_text == "Brak":
            return 49.84, 19.79 # Sułkowice
        url = f"https://nominatim.openstreetmap.org/search?q={location_text}&format=json&limit=1"
        headers = {'User-Agent': 'YapassBot/1.0'}
        try:
            r = requests.get(url, headers=headers).json()
            if r: return float(r[0]['lat']), float(r[0]['lon'])
        except: pass
        return 49.84, 19.79

    async def get_weather(self, dt, location_text):
        lat, lon = await self.get_coordinates(location_text)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability&start_date={dt.date()}&end_date={dt.date()}"
        try:
            r = requests.get(url).json()
            hour = dt.hour
            temp = r['hourly']['temperature_2m'][hour]
            rain = r['hourly']['precipitation_probability'][hour]
            return f"🌡️ {temp}°C, Opady: {rain}% (Lokalizacja: {lat:.2f}, {lon:.2f})"
        except: return "🌡️ Pogoda: Brak danych."

    @tasks.loop(minutes=1)
    async def daily_report(self):
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            channel = self.bot.get_channel(1468962094438158504)
            if not channel: return
            service = get_calendar_service()
            t_start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            t_end = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
            try:
                events = service.events().list(calendarId=os.getenv('CALENDAR_ID'), timeMin=t_start, timeMax=t_end, singleEvents=True, orderBy='startTime').execute().get('items', [])
                if not events: return
                conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
                for ev in events:
                    c.execute("SELECT 1 FROM sent_reminders WHERE event_id = ? AND sent_date = ?", (ev['id'], now.strftime('%Y-%m-%d')))
                    if c.fetchone(): continue
                    c.execute("SELECT user_id FROM participants WHERE event_name = ?", (ev['summary'],))
                    attendees = [f"<@{r[0]}>" for r in c.fetchall()]
                    embed = discord.Embed(title=f"🔔 Przypomnienie: {ev['summary']}", color=discord.Color.gold())
                    embed.add_field(name="Ekipa", value=", ".join(attendees) if attendees else "Brak zapisanych")
                    await channel.send(embed=embed)
                    c.execute("INSERT INTO sent_reminders (event_id, sent_date) VALUES (?, ?)", (ev['id'], now.strftime('%Y-%m-%d')))
                conn.commit(); conn.close()
            except Exception as e: print(f"Raport Error: {e}")

    @app_commands.command(name="kalendarz", description="Dodaj event")
    async def kalendarz(self, interaction: discord.Interaction, tytul: str, kiedy: str, ile_godzin: float = 1.0, miejsce: str = "Brak"):
        await interaction.response.defer()
        dt_start = dateparser.parse(kiedy, settings={'PREFER_DATES_FROM': 'future'})
        if not dt_start:
            await interaction.followup.send("❌ Nieprawidłowa data!"); return
        
        dt_end = dt_start + timedelta(hours=ile_godzin)
        service = get_calendar_service()
        conflicts = service.events().list(calendarId=os.getenv('CALENDAR_ID'), timeMin=dt_start.isoformat()+"Z", timeMax=dt_end.isoformat()+"Z", singleEvents=True).execute().get('items', [])
        
        if conflicts:
            await interaction.followup.send(f"⚠️ Kolizja z: **{conflicts[0]['summary']}**"); return

        weather = await self.get_weather(dt_start, miejsce)
        event_link = add_event(tytul, dt_start.isoformat(), dt_end.isoformat(), f"Pogoda: {weather}", miejsce)
        
        embed = discord.Embed(title=f"📅 {tytul}", url=event_link, color=discord.Color.green())
        embed.add_field(name="Start", value=dt_start.strftime('%d.%m %H:%M'), inline=True)
        embed.add_field(name="Pogoda", value=weather, inline=False)
        msg = await interaction.followup.send(embed=embed)
        for emoji in ["✅", "❌", "❓"]: await msg.add_reaction(emoji)

async def setup(bot):
    await bot.add_cog(Calendar(bot))