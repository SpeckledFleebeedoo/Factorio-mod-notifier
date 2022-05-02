import os
import botfunctions
import discord
from discord.ext import tasks
from discord.ext import commands
from dotenv import load_dotenv
import traceback

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"

intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX') + " "
help_command = commands.DefaultHelpCommand(no_category = "Commands")
bot = commands.Bot(command_prefix = PREFIX, intents = intents, help_command=help_command)

@bot.event
async def on_ready():
    guilds = bot.guilds
    updatelist = await botfunctions.firstStart(guilds)
    if updatelist:
        await send_update_messages(updatelist)
    if not check_mod_updates.is_running():
        check_mod_updates.start()
    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="the mod pipes"))
    appinfo = await bot.application_info()
    owner = appinfo.owner
    await owner.send("Mod update bot started!")

async def verify_user(ctx: commands.Context) -> bool:
    '''
    Verifies if users are either admin or have the proper role to interact with the restricted bot commands.
    '''
    permissions = ctx.channel.permissions_for(ctx.author)
    if permissions.administrator:
        return True
    else:
        servermodrole = await botfunctions.getModRole(str(ctx.guild.id))
        userroles = [str(role.id) for role in ctx.author.roles]
        if servermodrole in userroles:
            return True
        else:
            await ctx.send("You do not have the right permissions for this")
            return False

@bot.command()
@commands.check(verify_user)
async def set_channel(ctx, id):
    '''
    Sets the channel in which mod updates are posted.

    id can either be the ID of a channel or a channel mention.
    '''
    if id[0:2] == "<#":
        id = id[2:-1]
    if id.isnumeric():
        id = int(id)
        channel = bot.get_channel(id)
        if channel.guild == ctx.guild:
            await botfunctions.setChannel(ctx.guild.id, id)
            await ctx.send(f"Mod updates channel set to <#{id}>")
        else:
            await ctx.send("Invalid argument, please use a channel on this server")
    else:
        await ctx.send("Invalid argument, please use a channel link or ID")

@bot.command()
@commands.check(verify_user)
async def set_modrole(ctx, id):
    '''
    Sets the role needed to interact with the bot.

    Server admins can always use commands.
    id can either be a role ID or a role mention.
    '''
    if id.startswith("<@&"):
        id = id[3:-1]
    if id.isnumeric():
        id = int(id)
        await botfunctions.setModRole(ctx.guild.id, id)
        await ctx.send("Modrole changed")
    elif id == "None":
        await botfunctions.setModRole(ctx.guild.id, None)
        await ctx.send("Modrole reset")
    else:
        await ctx.send("Invalid argument")

@bot.command()
async def invite(ctx):
    '''
    Posts an invite link to add the bot to another server.
    '''
    await ctx.send("https://discord.com/api/oauth2/authorize?client_id=872540831599456296&permissions=19456&scope=bot")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Error: missing argument.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        appinfo = await bot.application_info()
        owner = appinfo.owner
        await owner.send(traceback.format_exc())

@bot.event
async def on_guild_join(guild):
    await botfunctions.addGuild(guild.id)

@bot.event
async def on_guild_remove(guild):
    await botfunctions.removeGuild(guild.id)

@tasks.loop(minutes=1)
async def check_mod_updates():
    try:
        updatelist = await botfunctions.checkUpdates()
        if updatelist != []:
            await send_update_messages(updatelist)
                      
    except discord.DiscordServerError:
        print("Discord server error")
        pass
    except:
        appinfo = await bot.application_info()
        owner = appinfo.owner
        await owner.send(traceback.format_exc())

async def send_update_messages(updatelist: list):
    for mod, tag in updatelist:
        name = mod[0]
        title = mod[2]
        owner = mod[3]
        version = mod[4]
        output = await create_embed(name, title, owner, version, tag)
        channels = await botfunctions.getChannels()
        for channelID in channels:
            channel = bot.get_channel(int(channelID[0]))
            await channel.send(embed=output)

async def create_embed(name: str, title: str, owner: str, version: str, tag: str):
    title = await botfunctions.make_safe(title)
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - len(TRIMMED)] + TRIMMED
    safeowner = await botfunctions.make_safe(owner)
    if tag == "u":
        embedtitle = f'**Updated mod:** \n{title}'
        color = 0x5865F2
    elif tag == "n":
        embedtitle = f'**New mod:** \n{title}'
        color = 0x2ECC71
    link = f'https://mods.factorio.com/mods/{owner}/{name}'.replace(" ", "%20")

    thumbnailURL = await botfunctions.getThumbnail(name)

    embed = discord.Embed(title=embedtitle, color=color, url=link)
    embed.add_field(name="Author", value=safeowner, inline=True)
    embed.add_field(name="Version:", value=version, inline=True)
    if thumbnailURL is not None:
        embed.set_thumbnail(url=thumbnailURL)
    return embed

bot.run(TOKEN)