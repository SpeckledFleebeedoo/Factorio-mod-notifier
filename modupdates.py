import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import requests #TODO: REPLACE WITH aiohttp

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"
DB_NAME = "mods.db"

class ModUpdates(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
    
    async def send_update_messages(self, updatelist: list):
        for mod, tag in updatelist:
            name = mod[0]
            title = mod[2]
            owner = mod[3]
            version = mod[4]
            output = await self.create_embed(name, title, owner, version, tag)
            channels = await self.getChannels()
            for channelID in channels:
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

        thumbnailURL = await self.getThumbnail(name)

        embed = discord.Embed(title=embedtitle, color=color, url=link)
        embed.add_field(name="Author", value=safeowner, inline=True)
        embed.add_field(name="Version:", value=version, inline=True)
        if thumbnailURL is not None:
            embed.set_thumbnail(url=thumbnailURL)
        return embed

    async def checkUpdates(self):
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
                mods = await self.getMods(url)
            except ConnectionError:
                break
            updatedmods = await self.compareMods(mods)
            if updatedmods != []:
                updatelist += updatedmods
            i += 1
            if len(updatedmods) != 10:
                modupdated = False
        return updatelist

    async def getMods(self, url: str) -> list:
        """
        Grabs the list of all mods from the API page and filters out the relevant entries. 
        Returns a list of mods, each following the format [name, release date, title, owner, version]
        """
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json()['results']
            mods = [[mod["name"], mod["latest_release"]["released_at"], mod["title"], mod["owner"], mod["latest_release"]["version"]] for mod in results if mod.get('latest_release') is not None]
            return mods
        else:
            raise ConnectionError("Failed to retrieve mod list")

    async def compareMods(self, mods: list) -> list:
        """
        Compares mods in list to entries stored in database. Sends list of updated mods to messager. 

        Returns a list of [name, release date, title, owner, version], tag
        """
        updatedmods = []
        with await sqlite3.connect(DB_NAME) as con:
            with await con.cursor() as cur:
                for mod in mods:
                    existing_entry = cur.execute("SELECT * FROM mods WHERE name=:name", {"name": mod[0]}).fetchall()
                    if existing_entry == []:
                        updatedmods.append([mod, "n"])
                        await cur.execute("INSERT INTO mods VALUES (?, ?, ?, ?, ?)", mod)
                    elif existing_entry[0][4] != mod[4]:
                        updatedmods.append([mod, "u"])
                        await cur.execute("INSERT OR REPLACE INTO mods VALUES (?, ?, ?, ?, ?)", mod)
                await con.commit()
        return updatedmods

    async def make_safe(self, string: str) -> str:
        """
        Escapes formatting to avoid unwanted behaviour in Discord messages.
        """
        return string.replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "@​\u200b")

    async def getThumbnail(self, name: str) -> str:
        """
        Finds the thumbnail for the specified mods.

        Returns either the URL or None if no thumbnail exists or the connection fails.
        """
        url = f"https://mods.factorio.com/api/mods/{name}"
        response = requests.get(url)
        if response.status_code == 200:
            json = response.json()
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

    async def getChannels(self) -> list:
        """
        Gets and returns a list of all set channel IDs
        """
        with await sqlite3.connect(DB_NAME) as con:
            with await con.cursor() as cur:
                channels = await cur.execute("SELECT updates_channel FROM guilds WHERE updates_channel IS NOT NULL").fetchall()
        return channels


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModUpdates(bot))