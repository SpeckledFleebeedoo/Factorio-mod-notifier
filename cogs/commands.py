import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import aiohttp
from fuzzywuzzy import process, fuzz
from math import log10
from misc import verify_user
import os

SHARED_VOLUME = "."
DB_NAME = f"{SHARED_VOLUME}/mods.db"

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
        Remove a mod from the list of subscriptions.
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
    async def find_mod(self, interaction: discord.Interaction, modname: str):
        """
        Find mods by name.
        """
        await interaction.response.send_message("Looking for mods...")
        mods = {name:title for name, title in self.modscache}
        #find exact matches
        foundmod = process.extractOne(modname, mods, scorer=fuzz.ratio) #[title, score, name]
        if foundmod[1] == 100: #Exact match found
            embed = await self.make_embed(foundmod[2])
        
        else: #find fuzzy matches
            foundmods = process.extract(modname, mods, scorer=fuzz.partial_ratio) #[title, score, name]

            highestscore = [None, None, 0]
            for mod in foundmods:
                name = mod[2]
                url = f"https://mods.factorio.com/api/mods/{name}"
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(url) as response:
                        if response.ok == True:
                            json = await response.json()
                            downloads_count = json["downloads_count"]
                        else:
                            downloads_count = 1
                score = mod[1]/50 * log10(downloads_count)
                if score > highestscore[2]:
                    highestscore = [mod[0], mod[2], score]
            
            embed = await self.make_embed(highestscore[1])
        await interaction.edit_original_response(content=None, embed=embed)
        
    async def make_embed(self, name: str):
        """
        Creates an embed for the search result.
        """
        url = f"https://mods.factorio.com/api/mods/{name}".replace(" ", "%20")
        userurl = f"https://mods.factorio.com/mod/{name}".replace(" ", "%20")
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as response:
                if response.ok == True:
                    json = await response.json()
                    owner = json["owner"].replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "@​\u200b")
                    embed = discord.Embed(title=json["title"], color=0x2ECC71, url=userurl, description=json["summary"])
                    embed.add_field(name="Owner", value=owner, inline=True)
                    embed.add_field(name="Downloads", value=json["downloads_count"], inline=True)
                    if "thumbnail" in json:
                        thumbnailraw = json["thumbnail"]
                        if thumbnailraw != "/assets/.thumb.png":
                            thumbnailURL = "https://assets-mod.factorio.com" + thumbnailraw
                            embed.set_thumbnail(url=thumbnailURL)
                    return embed
                else:
                    return None

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
        extensions = []
        for root, _, files in os.walk("cogs"):
            for file in files:
                path = os.path.join(root, file)
                if path.endswith(".py"):
                    extensions.append(path.split(".py")[0].replace(os.sep, "."))
        for extension in extensions:
            await self.bot.reload_extension(extension)
        await interaction.response.send_message("Cogs reloaded", ephemeral=True)

    @app_commands.command()
    async def botinfo(self, interaction: discord.Interaction):
        """
        Shows info about the bot.
        """
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            servers = cur.execute("SELECT * FROM guilds").fetchall()
            servercount = len(servers)
        embed = discord.Embed(colour=0x5865F2, title="Factorio Mod Notifier")
        embed.add_field(name="Number of servers", value=servercount, inline=False)
        embed.add_field(name="Creator", value="SpeckledFleebeedoo#8679 (<@247640901805932544>)", inline=False)
        embed.add_field(name="Source", value="[GitHub](https://www.github.com/SpeckledFleebeedoo/Factorio-mod-notifier)")
        embed.add_field(name="Invite link", value="[Invite](https://discord.com/api/oauth2/authorize?client_id=872540831599456296&permissions=274877925376&scope=bot%20applications.commands)")
        embed.add_field(name = "Info", value="To set up the bot on a new server, use /set_channel. No notifications will be sent without a channel set.")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandCog(bot))