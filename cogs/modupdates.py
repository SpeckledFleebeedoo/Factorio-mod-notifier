import discord
from discord.ext import commands
from discord.ext import tasks
import sqlite3
import aiohttp
import traceback
import logging
from misc import get_mods

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"
DB_NAME = "mods.db"

class ModUpdates(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.check_mod_updates.start()
    
    def cog_unload(self) -> None:
        self.check_mod_updates.cancel()
    
    @tasks.loop(minutes=1)
    async def check_mod_updates(self):
        try:
            updatelist = await self.check_updates()
            if updatelist != []:
                await self.send_update_messages(updatelist)

        except discord.DiscordServerError:
            logging.warning("Discord server error")
            pass
        except Exception as error:
            logging.warning(f"{error} checking mod updates")
            logging.debug(f"Traceback:{traceback.format_exc()}")
            appinfo = await self.bot.application_info()
            owner = appinfo.owner
            await owner.send(traceback.format_exc())
    
    async def send_update_messages(self, updatelist: list):
        for mod, tag in updatelist:
            name = mod[0]
            title = mod[2]
            owner = mod[3]
            version = mod[4]
            output = await self.create_embed(name, title, owner, version, tag)
            
            with sqlite3.connect(DB_NAME) as con:
                cur = con.cursor()
                channels = cur.execute("SELECT updates_channel FROM guilds WHERE updates_channel IS NOT NULL").fetchall()
            for channelID in channels:
                subscriptions = cur.execute("SELECT subscribedmods FROM guilds WHERE updates_channel = (?)", channelID).fetchall()[0][0]
                if subscriptions != None:
                    subscriptions = subscriptions.split(", ")
                if subscriptions == None or name in subscriptions:
                    channel = self.bot.get_channel(int(channelID[0]))
                    await channel.send(embed=output)
                    
    async def create_embed(self, name: str, title: str, owner: str, version: str, tag: str):
        title = await self.make_safe(title)
        if len(title) > MAX_TITLE_LENGTH:
            title = title[:MAX_TITLE_LENGTH - len(TRIMMED)] + TRIMMED
        safeowner = await self.make_safe(owner)
        if tag == "u":
            embedtitle = f'**Updated mod:** \n{title}'
            color = 0x5865F2
        elif tag == "n":
            embedtitle = f'**New mod:** \n{title}'
            color = 0x2ECC71
        link = f'https://mods.factorio.com/mods/{owner}/{name}'.replace(" ", "%20")

        thumbnailURL = await self.get_thumbnail(name)

        embed = discord.Embed(title=embedtitle, color=color, url=link)
        embed.add_field(name="Author", value=safeowner, inline=True)
        embed.add_field(name="Version:", value=version, inline=True)
        if thumbnailURL is not None:
            embed.set_thumbnail(url=thumbnailURL)
        return embed

    async def check_updates(self):
        """
        Iterates through pages of recently updated mods until unchanged mods are found.

        Returns a list of [name, release date, title, owner, version]
        """
        modupdated = True
        i = 1
        updatelist = []
        while modupdated == True:
            url = f"https://mods.factorio.com/api/mods?page_size=10&page={i}&sort=updated_at&sort_order=desc"
            try:
                mods = await get_mods(url)
            except ConnectionError:
                logging.warning("Connection Error while getting modlist")
                break
            updatedmods = await self.compare_mods(mods)
            if updatedmods != []:
                updatelist += updatedmods
            i += 1
            if len(updatedmods) != 10:
                modupdated = False
        return updatelist

    async def compare_mods(self, mods: list) -> list:
        """
        Compares mods in list to entries stored in database. Sends list of updated mods to messager. 

        Returns a list of [name, release date, title, owner, version], tag
        """
        updatedmods = []
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            for mod in mods:
                existing_entry = cur.execute("SELECT * FROM mods WHERE name=:name", {"name": mod[0]}).fetchall()
                if existing_entry == []:
                    updatedmods.append([mod, "n"])
                    cur.execute("INSERT INTO mods VALUES (?, ?, ?, ?, ?)", mod)
                elif existing_entry[0][4] != mod[4]:
                    updatedmods.append([mod, "u"])
                    cur.execute("INSERT OR REPLACE INTO mods VALUES (?, ?, ?, ?, ?)", mod)
            con.commit()
        return updatedmods

    async def make_safe(self, string: str) -> str:
        """
        Escapes formatting to avoid unwanted behaviour in Discord messages.
        """
        return string.replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "@​\u200b")

    async def get_thumbnail(self, name: str) -> str:
        """
        Finds the thumbnail for the specified mods.

        Returns either the URL or None if no thumbnail exists or the connection fails.
        """
        url = f"https://mods.factorio.com/api/mods/{name}"
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as response:
                if response.ok == True:
                    json = await response.json()
                    if "thumbnail" in json:
                        thumbnailraw = json["thumbnail"]
                    else:
                        return None
                    if thumbnailraw != "/assets/.thumb.png":
                        thumbnailURL = "https://assets-mod.factorio.com" + thumbnailraw
                        return thumbnailURL
                    else:
                        return None
                else:
                    return None

    async def get_channels(self) -> list:
        """
        Gets and returns a list of all set channel IDs
        """
        


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModUpdates(bot))