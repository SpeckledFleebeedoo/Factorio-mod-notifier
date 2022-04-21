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
    botfunctions.firstStart()
    check_mod_updates.start()
    user = await client.fetch_user("247640901805932544")
    await user.send("Mod update bot started!")

@tasks.loop(minutes=10)
async def check_mod_updates():
    try:
        updatelists = botfunctions.checkUpdates()
        if updatelists != []:
            for updatelist in updatelists:
                output = botfunctions.writeMessage(updatelist)
                channel = client.get_channel(CHANNEL)
                await channel.send(output)
                
    except discord.DiscordServerError:
        print("Discord server error")
        pass
    except:
        user = await client.fetch_user("247640901805932544")
        await user.send(traceback.format_exc())

client.run(TOKEN)