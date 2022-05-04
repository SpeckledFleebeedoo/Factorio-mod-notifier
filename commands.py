import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from verification import verify_user

DB_NAME = "mods.db"

class CommandCog(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    async def invite(self, interaction:discord.Interaction):
        '''
        Posts an invite link for adding the bot to another server.
        '''
        await interaction.response.send_message("Link")

    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    @app_commands.check(verify_user)
    async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        '''
        Sets the channel in which mod updates are posted.
        '''
        with await sqlite3.connect(DB_NAME) as con:
            with await con.cursor() as cur:
                await cur.execute("UPDATE guilds SET updates_channel = (?) WHERE id = (?)", [str(channel.id), str(interaction.guild.id)])
                await con.commit()
        await interaction.response.send_message(f"Mod updates channel set to <#{channel.id}>", ephemeral=True)

    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    @app_commands.check(verify_user)
    async def set_modrole(interaction: discord.Interaction, role: discord.Role):
        '''
        Sets the role needed to change bot settings. Server admins always can.
        '''
        with await sqlite3.connect(DB_NAME) as con:
            with await con.cursor() as cur:
                await cur.execute("UPDATE guilds SET modrole = (?) WHERE id = (?)", [str(role.id), str(interaction.guild.id)])
                await con.commit()
        await interaction.response.send_message(f"Modrole set to <@&{role.id}>", ephemeral=True)

    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    async def sync_commands(self, interaction: discord.Interaction):
        """
        Synchronize all commands with source code.
        """
        await self.bot.tree.sync(guild=discord.Object(763041705024552990))
        await interaction.response.send_message("Commands synchronized", ephemeral=True)
    
    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    async def update_cogs(self, interaction: discord.Interaction):
        """
        Reload all cogs.
        """
        await interaction.response.send_message("Reloading cogs", ephemeral=True)
        await self.bot.reload_extension("commands")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandCog(bot))