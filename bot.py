import os
import botfunctions
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))

client = discord.Client()

@client.event
async def on_ready():
    client.oldModList = botfunctions.getMods()
    check_mod_updates.start()

@tasks.loop(minutes=10)
async def check_mod_updates():
    newModList = botfunctions.getMods()
    updatedList = botfunctions.checkUpdates(client.oldModList, newModList)
    client.oldModList = newModList
    if updatedList is not None:
        output = botfunctions.writeMessage(updatedList)
        channel = client.get_channel(CHANNEL)
        await channel.send(output)

client.run(TOKEN)