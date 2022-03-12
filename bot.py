import os
import botfunctions
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import traceback

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))

client = discord.Client()

@client.event
async def on_ready():
    client.ModList = botfunctions.getMods()
    check_mod_updates.start()
    user = await client.fetch_user("247640901805932544")
    await user.send("Mod update bot started!")

@tasks.loop(minutes=10)
async def check_mod_updates():
    try:
        newModList = botfunctions.getMods()
        if newModList != None:
            updatedList = botfunctions.checkUpdates(client.ModList, newModList)
            client.ModList = newModList
            if updatedList is not None:
                output = botfunctions.writeMessage(updatedList)
                channel = client.get_channel(CHANNEL)
                await channel.send(output)
    except DiscordServerError:
        print("Discord server error")
        pass
    except:
        user = await client.fetch_user("247640901805932544")
        await user.send(traceback.format_exc())

client.run(TOKEN)