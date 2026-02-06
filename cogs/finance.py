import discord
from discord import app_commands
from discord.ext import commands
import sqlite3

# --- WIDOK Z FILTROWANĄ LISTĄ WYBORU ---
class DebtSelectView(discord.ui.View):
    def __init__(self, creditor, kwota, opis, members):
        super().__init__(timeout=60)
        self.creditor = creditor
        self.kwota = kwota
        self.opis = opis
        
        options = []
        for member in members:
            if member.id != creditor.id:
                options.append(discord.SelectOption(
                    label=member.display_name, 
                    value=str(member.id),
                    description=f"Oznacz {member.display_name} jako dłużnika"
                ))

        self.add_item(discord.ui.Select(
            placeholder="Wybierz dłużników z tego kanału...",
            min_values=1,
            max_values=min(len(options), 15) if options else 1,
            options=options if options else [discord.SelectOption(label="Brak innych osób", value="0")],
            disabled=not options
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.creditor.id

    async def handle_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        debtor_ids = [int(val) for val in select.values]
        all_participants_count = len(debtor_ids) + 1
        share = round(self.kwota / all_participants_count, 2)
        
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        debtors_text = []
        for d_id in debtor_ids:
            member = interaction.guild.get_member(d_id)
            name = member.display_name if member else "Nieznany"
            
            c.execute("INSERT INTO debts (debtor_id, debtor_name, creditor_id, creditor_name, amount, description) VALUES (?, ?, ?, ?, ?, ?)",
                      (d_id, name, self.creditor.id, self.creditor.display_name, share, self.opis))
            debtors_text.append(f"• **{name}**: {share} zł")
        
        conn.commit()
        conn.close()

        embed = discord.Embed(title="✅ ROZLICZENIE ZATWIERDZONE", color=0x2ecc71)
        embed.description = (
            f"**{self.creditor.display_name}** wyłożył **{self.kwota} zł** za *{self.opis}*.\n"
            f"Koszt podzielony na **{all_participants_count}** osób (po **{share} zł**)."
        )
        embed.add_field(name="ZAPISANE DŁUGI:", value="\n".join(debtors_text))
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

class Finance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rozlicz", description="Inicjuje podział kosztów między wybrane osoby z tego kanału")
    @app_commands.describe(kwota="Ile łącznie zapłaciłeś?", opis="Za co płaciłeś? (np. Pizza)")
    async def rozlicz(self, interaction: discord.Interaction, kwota: float, opis: str):
        channel = interaction.channel
        eligible_members = []
        
        for member in interaction.guild.members:
            if member.bot: continue
            permissions = channel.permissions_for(member)
            if permissions.view_channel:
                eligible_members.append(member)

        if len(eligible_members) < 2:
            await interaction.response.send_message("❌ Nie ma kogo rozliczyć na tym kanale (poza Tobą).", ephemeral=True)
            return

        embed = discord.Embed(
            title="💰 DZIELENIE KOSZTÓW",
            description=f"Zapłaciłeś **{kwota} zł** za **{opis}**.\n\nWybierz dłużników spośród osób mających dostęp do tego kanału:",
            color=0x58a6ff
        )
        
        view = DebtSelectView(interaction.user, kwota, opis, eligible_members)
        view.children[0].callback = lambda i: view.handle_select(i, view.children[0])
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="moje_dlugi", description="Wyświetla listę Twoich długów oraz należności")
    async def moje_dlugi(self, interaction: discord.Interaction):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        c.execute("SELECT creditor_name, SUM(amount) FROM debts WHERE debtor_id = ? GROUP BY creditor_id", (interaction.user.id,))
        to_pay = c.fetchall()
        
        c.execute("SELECT debtor_name, SUM(amount) FROM debts WHERE creditor_id = ? GROUP BY debtor_id", (interaction.user.id,))
        to_receive = c.fetchall()
        conn.close()

        embed = discord.Embed(title=f"📊 SALDO: {interaction.user.display_name.upper()}", color=0x3498db)
        
        pay_txt = "\n".join([f"• Dla **{r[0]}**: {r[1]:.2f} zł" for r in to_pay]) if to_pay else "_Brak długów! 🎉_"
        rec_txt = "\n".join([f"• Od **{r[0]}**: {r[1]:.2f} zł" for r in to_receive]) if to_receive else "_Nikt Ci nic nie wisi..._"
        
        embed.add_field(name="📉 MUSISZ ODDAĆ", value=pay_txt, inline=False)
        embed.add_field(name="📈 TWOJE NALEŻNOŚCI", value=rec_txt, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="oddalem", description="Usuwa Twoje zadłużenie wobec wybranej osoby")
    @app_commands.describe(komu="Osoba, której oddałeś pieniądze")
    async def oddalem(self, interaction: discord.Interaction, komu: discord.Member):
        conn = sqlite3.connect('bot_data.db'); c = conn.cursor()
        
        c.execute("SELECT SUM(amount) FROM debts WHERE debtor_id = ? AND creditor_id = ?", (interaction.user.id, komu.id))
        result = c.fetchone()
        
        if result[0] is None or result[0] == 0:
            await interaction.response.send_message(f"ℹ️ Nie masz zarejestrowanych długów wobec **{komu.display_name}**.", ephemeral=True)
            conn.close()
            return

        c.execute("DELETE FROM debts WHERE debtor_id = ? AND creditor_id = ?", (interaction.user.id, komu.id))
        conn.commit(); conn.close()
        
        await interaction.response.send_message(f"✅ Rozliczono! Twoje długi wobec **{komu.display_name}** zostały wyczyszczone.", ephemeral=False)

async def setup(bot):
    await bot.add_cog(Finance(bot))