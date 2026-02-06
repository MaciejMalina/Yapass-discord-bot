import discord
from discord import app_commands
from discord.ext import commands
import sqlite3

class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="todo_dodaj")
    @app_commands.describe(lista="Nazwa listy (np. zakupy, projekty)", rzecz="Treść zadania do wykonania")
    async def todo_add(self, interaction: discord.Interaction, lista: str, rzecz: str):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("INSERT INTO todo (category, item, user) VALUES (?, ?, ?)", (lista.lower(), rzecz, interaction.user.display_name))
        conn.commit(); conn.close()
        await interaction.response.send_message(f"➕ Dodano **{rzecz}** do listy **{lista}**.")

    @app_commands.command(name="todo_pokaz")
    @app_commands.describe(lista="Nazwa listy, którą chcesz podejrzeć")
    async def todo_show(self, interaction: discord.Interaction, lista: str):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT item, user FROM todo WHERE category = ?", (lista.lower(),))
        rows = c.fetchall(); conn.close()
        if not rows:
            await interaction.response.send_message(f"Lista **{lista}** jest pusta."); return
        items = "\n".join([f"• {r[0]} (od: {r[1]})" for r in rows])
        await interaction.response.send_message(embed=discord.Embed(title=f"📋 Lista: {lista}", description=items, color=discord.Color.orange()))

    @app_commands.command(name="todo_wyczysc")
    @app_commands.describe(lista="Nazwa listy do całkowitego wyczyszczenia")
    async def todo_clear(self, interaction: discord.Interaction, lista: str):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("DELETE FROM todo WHERE category = ?", (lista.lower(),))
        conn.commit(); conn.close()
        await interaction.response.send_message(f"🧹 Wyczyszczono listę **{lista}**.")

    @app_commands.command(name="todo_wszystkie", description="Wyświetla wszystkie listy TODO")
    async def todo_all(self, interaction: discord.Interaction):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT category, item, user FROM todo ORDER BY category ASC")
        rows = c.fetchall(); conn.close()
        if not rows:
            await interaction.response.send_message("📭 Brak zadań."); return
        todo_map = {}
        for cat, item, user in rows:
            if cat not in todo_map: todo_map[cat] = []
            todo_map[cat].append(f"• {item} (@{user})")
        embed = discord.Embed(title="📋 Wszystkie listy TODO", color=discord.Color.blue())
        for cat, items in todo_map.items():
            embed.add_field(name=cat.upper(), value="\n".join(items), inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Todo(bot))