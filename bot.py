import os
import botfunctions
import discord
from discord.ext import tasks
from dotenv import load_dotenv
from collections import deque

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))

client = discord.Client()

@client.event
async def on_ready():
    client.ModLists = deque([botfunctions.getMods()], 2)
    check_mod_updates.start()

@tasks.loop(minutes=10)
async def check_mod_updates():
    client.ModLists.append(botfunctions.getMods())
    updatedList = botfunctions.checkUpdates(client.ModLists[0], client.ModLists[1])
    if updatedList is not None:
        output = botfunctions.writeMessage(updatedList)
        channel = client.get_channel(CHANNEL)
        await channel.send(output)

client.run(TOKEN)