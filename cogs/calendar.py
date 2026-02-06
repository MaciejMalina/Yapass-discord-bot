import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import sqlite3
import dateparser
import requests
import psutil
from datetime import datetime, timedelta
from calendar_utils import add_event, get_calendar_service

class Calendar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_report.start()

    # --- POMOCNICZA LOGIKA POGODY ---
    async def get_weather_info(self, dt, location_text):
        if not location_text or location_text == "Brak":
            return "🌡️ Brak danych"
        try:
            import urllib.parse
            encoded_loc = urllib.parse.quote(location_text)
            
            geo_url = f"https://nominatim.openstreetmap.org/search?q={encoded_loc}&format=json&limit=1&addressdetails=1"
            headers = {
                'User-Agent': 'YapassDiscordBot/1.0'
            }
            
            geo_r = requests.get(geo_url, headers=headers).json()
            
            if not geo_r:
                simple_loc = location_text.split(',')[0].strip()
                geo_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(simple_loc)}&format=json&limit=1"
                geo_r = requests.get(geo_url, headers=headers).json()
                
            if not geo_r:
                return "🌡️ Nie znaleziono lokalizacji"

            lat, lon = float(geo_r[0]['lat']), float(geo_r[0]['lon'])

            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&start_date={dt.date()}&end_date={dt.date()}"
            w_r = requests.get(weather_url).json()
            
            hour = dt.hour
            temp = w_r['hourly']['temperature_2m'][hour]
            code = w_r['hourly']['weathercode'][hour]

            emoji = "☀️" if code < 3 else "☁️" if code < 50 else "🌧️" if code < 80 else "❄️"
            return f"{emoji} {temp}°C"
            
        except Exception as e:
            print(f"Błąd pogodowy: {e}")
            return "🌡️ Błąd pogody"

    # --- LOGIKA REAKCJI (ZLICZANIE OSÓB) ---
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name == "✅" and not payload.member.bot:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if message.embeds:
                event_name = message.embeds[0].title.replace("📅 ", "").replace("🔔 Przypomnienie: ", "").replace("🔔 ", "")
                conn = sqlite3.connect('bot_data.db')
                c = conn.cursor()
                c.execute("SELECT 1 FROM participants WHERE message_id = ? AND user_id = ?", (payload.message_id, payload.user_id))
                if not c.fetchone():
                    c.execute("INSERT INTO participants (message_id, user_id, username, event_name) VALUES (?, ?, ?, ?)",
                              (payload.message_id, payload.user_id, payload.member.display_name, event_name))
                    conn.commit()
                conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.emoji.name == "✅":
            conn = sqlite3.connect('bot_data.db')
            c = conn.cursor()
            c.execute("DELETE FROM participants WHERE message_id = ? AND user_id = ?", (payload.message_id, payload.user_id))
            conn.commit()
            conn.close()

    # --- RAPORT 9:00 ---
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
                events_result = service.events().list(
                    calendarId=os.getenv('CALENDAR_ID'), 
                    timeMin=t_start, 
                    timeMax=t_end, 
                    singleEvents=True, 
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])

                if not events:
                    return 

                conn = sqlite3.connect('bot_data.db')
                c = conn.cursor()
                
                for ev in events:
                    event_id = ev['id']
                    summary = ev.get('summary', 'Bez tytułu')
                    
                    c.execute("SELECT 1 FROM sent_reminders WHERE event_id = ? AND sent_date = ?", 
                              (event_id, now.strftime('%Y-%m-%d')))
                    if c.fetchone(): continue
                    
                    location = ev.get('location', 'Brak lokalizacji')
                    description = ev.get('description', '')

                    c.execute("SELECT user_id FROM participants WHERE event_name = ?", (summary,))
                    at = [f"<@{r[0]}>" for r in c.fetchall()]
                    
                    weather_line = "Brak danych"
                    for line in description.split('\n'):
                        if "Pogoda:" in line:
                            weather_line = line.replace("Pogoda:", "").strip()
                            break

                    start_time_raw = ev['start'].get('dateTime', ev['start'].get('date'))
                    dt_obj = datetime.fromisoformat(start_time_raw.replace('Z', ''))

                    embed = discord.Embed(title=f"🔔 DZISIAJ: {summary}", color=discord.Color.gold())
                    embed.add_field(name="🕒 Start", value=f"**{dt_obj.strftime('%H:%M')}**", inline=True)
                    embed.add_field(name="📍 Miejsce", value=location, inline=True)
                    embed.add_field(name="🌡️ Pogoda", value=weather_line, inline=False)
                    embed.add_field(name="👥 Ekipa", value=", ".join(at) if at else "_Nikt się nie zapisał 😢_", inline=False)
                    
                    await channel.send(embed=embed)
                    
                    c.execute("INSERT INTO sent_reminders (event_id, sent_date) VALUES (?, ?)", 
                              (event_id, now.strftime('%Y-%m-%d')))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"Błąd raportu: {e}")

    # --- KOMENDA /KALENDARZ ---
    @app_commands.command(name="kalendarz", description="Dodaj wydarzenie do kalendarza")
    @app_commands.describe(tytul="Nazwa wydarzenia", kiedy="np. jutro 20:00", miejsce="np. Sułkowice")
    async def kalendarz(self, interaction: discord.Interaction, tytul: str, kiedy: str, ile_godzin: float = 1.0, miejsce: str = "Brak"):
        await interaction.response.defer()
        dt_start = dateparser.parse(kiedy, settings={'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'})
        if not dt_start:
            await interaction.followup.send("❌ Błędna data!"); return
            
        dt_end = dt_start + timedelta(hours=ile_godzin)
        weather = await self.get_weather_info(dt_start, miejsce)
        
        event_link = add_event(tytul, dt_start.isoformat(), dt_end.isoformat(), f"Pogoda: {weather}", miejsce)
        
        embed = discord.Embed(
            title=f"📅 {tytul}", 
            url=event_link, 
            description=f"📍 **Miejsce:** {miejsce} ({weather})\n⏰ **Start:** {dt_start.strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.green()
        )
        embed.set_footer(text="Kliknij ✅ aby się zapisać!")
        
        msg = await interaction.followup.send(embed=embed)
        await msg.add_reaction("✅")

    # --- KOMENDA /STATUS ---
    @app_commands.command(name="status", description="Sprawdza parametry życiowe bota i serwera")
    async def status(self, interaction: discord.Interaction):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        uptime = str(datetime.now() - self.bot.start_time).split('.')[0]
        
        embed = discord.Embed(title="🖥️ Status Systemu Yapass", color=discord.Color.blue())
        embed.add_field(name="CPU Usage", value=f"**{cpu}%**", inline=True)
        embed.add_field(name="RAM Usage", value=f"**{ram}%**", inline=True)
        embed.add_field(name="Uptime bota", value=f"**{uptime}**", inline=False)
        embed.set_footer(text=f"Host: Raspberry Pi 4B | Docker Container")
        
        await interaction.response.send_message(embed=embed)

    # --- KOMENDA /LISTA_EVENTOW ---
    @app_commands.command(name="lista_eventow", description="Pokazuje listę nadchodzących wydarzeń wraz z lokalizacją i pogodą")
    async def lista_eventow(self, interaction: discord.Interaction):
        await interaction.response.defer()
        service = get_calendar_service()
        now = datetime.utcnow().isoformat() + 'Z'
        
        try:
            events_result = service.events().list(
                calendarId=os.getenv('CALENDAR_ID'), 
                timeMin=now,
                maxResults=10, 
                singleEvents=True, 
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                await interaction.followup.send("📭 Brak nadchodzących wydarzeń w kalendarzu."); return

            embed = discord.Embed(title="📅 NADCHODZĄCE WYDARZENIA", color=0x238636)
            description_text = ""
            
            for i, ev in enumerate(events, 1):
                summary = ev.get('summary', 'Bez tytułu').upper()
                event_id = ev.get('id')
                location = ev.get('location', 'Brak lokalizacji')
                
                desc = ev.get('description', '')
                weather_info = "Brak danych"
                for line in desc.split('\n'):
                    if "Pogoda:" in line:
                        weather_info = line.replace("Pogoda:", "").strip()
                        break

                start = ev['start'].get('dateTime', ev['start'].get('date'))
                dt_obj = datetime.fromisoformat(start.replace('Z', ''))
                pretty_date = dt_obj.strftime('%d.%m %H:%M')
                
                description_text += (
                    f"**{i}. {summary}**\n"
                    f"> ⏰ Start: **{pretty_date}**\n"
                    f"> 📍 Miejsce: **{location}**\n"
                    f"> ☁️ Pogoda: **{weather_info}**\n"
                    f"> 🆔 ID: `{event_id}`\n\n"
                )

            embed.description = description_text
            embed.set_footer(text="Aby usunąć wydarzenie, wpisz: /usun [ID z listy]")
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Błąd API Google: {e}")

    # --- KOMENDA /USUN ---
    @app_commands.command(name="usun", description="Usuwa konkretne wydarzenie z kalendarza")
    @app_commands.describe(event_id="Wklej tutaj ID wydarzenia z listy")
    async def usun(self, interaction: discord.Interaction, event_id: str):
        await interaction.response.defer()
        service = get_calendar_service()
        try:
            service.events().delete(calendarId=os.getenv('CALENDAR_ID'), eventId=event_id).execute()
            await interaction.followup.send(f"✅ Pomyślnie usunięto wydarzenie: `{event_id}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Nie znaleziono wydarzenia o takim ID.")

async def setup(bot):
    await bot.add_cog(Calendar(bot))