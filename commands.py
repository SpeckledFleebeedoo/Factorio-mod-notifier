import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from misc import verify_user

DB_NAME = "mods.db"

class CommandCog(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.update_mods_cache.start()
    
    def cog_unload(self) -> None:
        self.update_mods_cache.cancel()
    
    @tasks.loop(minutes=20)
    async def update_mods_cache(self):
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            modslist = cur.execute("SELECT name, title FROM mods").fetchall()
            self.modscache = [name for name in modslist]

    @app_commands.command()
    async def invite(self, interaction:discord.Interaction):
        '''
        Posts an invite link for adding the bot to another server.
        '''
        await interaction.response.send_message("https://discord.com/api/oauth2/authorize?client_id=872540831599456296&permissions=19456&scope=bot")

    @app_commands.command()
    @app_commands.check(verify_user)
    @app_commands.guild_only()
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        '''
        Sets the channel in which mod updates are posted.
        '''
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("UPDATE guilds SET updates_channel = (?) WHERE id = (?)", [str(channel.id), str(interaction.guild_id)])
            con.commit()
        await interaction.response.send_message(f"Mod updates channel set to <#{channel.id}>", ephemeral=False)

    @app_commands.command()
    @app_commands.check(verify_user)
    @app_commands.guild_only()
    async def set_modrole(self, interaction: discord.Interaction, role: discord.Role):
        '''
        Sets the role needed to change bot settings. Server admins always can.
        '''
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("UPDATE guilds SET modrole = (?) WHERE id = (?)", [str(role.id), str(interaction.guild_id)])
            con.commit()
        await interaction.response.send_message(f"Modrole set to <@&{role.id}>", ephemeral=False)
    
    @app_commands.command()
    @app_commands.check(verify_user)
    @app_commands.guild_only()
    async def add_subscription(self, interaction: discord.Interaction, modname: str):
        """
        Add a mod to the subscription list of this server.

        Notifications will only be sent for subscribed mods. Autocomplete may take up to 20 minutes to update.
        """
        with sqlite3.connect(DB_NAME) as con:
            if modname in [name for name, _ in self.modscache]:
                cur = con.cursor()
                subscribedmods = cur.execute("SELECT subscribedmods FROM guilds WHERE id = (?)", [str(interaction.guild_id)]).fetchall()[0][0]
                
                if subscribedmods is not None:
                    subscribedmods = subscribedmods.split(", ")
                    if modname not in subscribedmods:
                        subscribedmods.append(modname)
                        subscribedmods = ", ".join(subscribedmods)
                        cur.execute("UPDATE guilds SET subscribedmods = (?) WHERE id = (?)", [subscribedmods, str(interaction.guild_id)])
                        con.commit()
                        await interaction.response.send_message(f"{modname} added to subscription list", ephemeral=False)
                    else:
                        await interaction.response.send_message(f"{modname} already in subscription list", ephemeral=True)
                else: 
                    subscribedmods = modname
                    cur.execute("UPDATE guilds SET subscribedmods = (?) where id = (?)", [subscribedmods, str(interaction.guild_id)])
                    con.commit()
                    await interaction.response.send_message(f"{modname} added to subscription list", ephemeral=False)
            else:
                await interaction.response.send_message("Invalid mod name", ephemeral=True)
    
    @add_subscription.autocomplete("modname")
    async def modname_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=title, value=name) for name, title in self.modscache if current.lower() in name.lower()][0:25]

    @app_commands.command()
    @app_commands.check(verify_user)
    @app_commands.guild_only()
    async def show_subscriptions(self, interaction: discord.Interaction):
        """
        Shows the mods this server is subscribed to.
        """
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            subscribedmods = cur.execute("SELECT subscribedmods FROM guilds WHERE id = (?)", [str(interaction.guild_id)]).fetchall()[0][0]
            if subscribedmods is not None:
                await interaction.response.send_message(f"Mods this server is subscribed to: {subscribedmods}", ephemeral=False)
            else:
                await interaction.response.send_message("This server is not subscribed to any mods. All updates will be sent.", ephemeral=False)

    @app_commands.command()
    @app_commands.check(verify_user)
    @app_commands.guild_only()
    async def remove_subscription(self, interaction: discord.Interaction, modname: str):
        """
        Shows the mods this server is subscribed to.
        """
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            modslist = cur.execute("SELECT subscribedmods FROM guilds WHERE id = (?)", [str(interaction.guild_id)]).fetchall()[0][0]
            modslist = modslist.split(", ")
            if modname in modslist:
                modslist.remove(modname)
                modslist = ", ".join(modslist)
                if modslist == "":
                    modslist = None
                cur.execute("UPDATE guilds SET subscribedmods = (?) WHERE id = (?)", [modslist, str(interaction.guild_id)])
                con.commit()
                if modslist == None:
                    await interaction.response.send_message(f"{modname} removed from subscriptions. \n\nSubscription list empty, sending all mod updates.", ephemeral=False)
                else: 
                    await interaction.response.send_message(f"{modname} removed from subscriptions", ephemeral=False)
            else:
                await interaction.response.send_message(f"{modname} not found in subscriptions", ephemeral=True)

    @remove_subscription.autocomplete("modname")
    async def unsub_autocomplete(self, interaction: discord.Interaction, current: str):
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            modslist = cur.execute("SELECT subscribedmods FROM guilds WHERE id = (?)", [str(interaction.guild_id)]).fetchall()[0][0]
            if modslist != None:
                modslist = modslist.split(", ")
                return [app_commands.Choice(name=name, value=name) for name in modslist if current.lower() in name.lower()]
            else:
                return []

    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    @commands.is_owner()
    async def update_commands(self, interaction: discord.Interaction):
        """
        Synchronize all commands with source code.
        """
        await self.bot.tree.sync()
        await interaction.response.send_message("Commands synchronized", ephemeral=True)

    @app_commands.command()
    @app_commands.guilds(763041705024552990)
    @commands.is_owner()
    async def update_cogs(self, interaction: discord.Interaction):
        """
        Reload all cogs.
        """
        await self.bot.reload_extension("commands")
        await interaction.response.send_message("Cogs reloaded", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandCog(bot))