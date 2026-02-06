import discord
from discord import app_commands
from discord.ext import commands
import sqlite3

class Finance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wydatek")
    async def spend(self, interaction: discord.Interaction, kwota: float, opis: str):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("INSERT INTO finance (payer, amount, description, date) VALUES (?, ?, ?, date('now'))",
                  (interaction.user.display_name, kwota, opis))
        conn.commit(); conn.close()
        await interaction.response.send_message(f"💰 Dodano: {kwota} zł za {opis}.")

    @app_commands.command(name="rozlicz")
    async def summary(self, interaction: discord.Interaction):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT payer, SUM(amount) FROM finance GROUP BY payer")
        rows = c.fetchall(); conn.close()
        embed = discord.Embed(title="📊 Bilans", color=discord.Color.green())
        for u, t in rows: embed.add_field(name=u, value=f"{t:.2f} zł")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Finance(bot))