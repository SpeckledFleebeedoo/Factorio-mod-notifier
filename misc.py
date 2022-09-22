import discord
import sqlite3
import aiohttp
from discord.ext import commands

SHARED_VOLUME = "."
DB_NAME = f"{SHARED_VOLUME}/mods.db"

async def verify_user(interaction: discord.Interaction) -> bool:
    '''
    Verifies if users are either admin or have the proper role to interact with the restricted bot commands.
    '''
    permissions = interaction.channel.permissions_for(interaction.user)
    if permissions.administrator:
        return True
    else:
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            roles = cur.execute("SELECT modrole FROM guilds WHERE id = (?)", [str(interaction.guild.id)]).fetchall()
            servermodrole = roles[0][0]
        userroles = [str(role.id) for role in interaction.user.roles]
        if servermodrole in userroles:
            return True
        else:
            await interaction.response.send_message("You do not have the right permissions for this", ephemeral=True)
            return False

async def get_mods(url: str) -> list:
    """
    Grabs the list of all mods from the API page and filters out the relevant entries. 
    Returns a list of mods, each following the format [name, release date, title, owner, version]
    """
    async with aiohttp.ClientSession() as cs:
        async with cs.get(url) as response:
            if response.ok == True:
                json = await response.json()
                results = json['results']
                mods = [[mod["name"], mod["latest_release"]["released_at"], mod["title"], mod["owner"], mod["latest_release"]["version"]] for mod in results if mod.get('latest_release') is not None]
                return mods
            else:
                raise ConnectionError("Failed to retrieve mod list")