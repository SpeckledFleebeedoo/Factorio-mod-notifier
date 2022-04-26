import requests
import sqlite3

con = sqlite3.connect("mods.db")
cur = con.cursor()

async def firstStart(guilds) -> list:
    """
    Checks if the database already exists.
    Will update database if it exists, or create a new database if not.

    Returns a list of [name, release date, title, owner, version] if database exists already, else None
    """
    cur.execute(''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name='guilds' ''')
    if cur.fetchone()[0]==1: #Guilds table already exists
        for guild in guilds:
            guildentries = cur.execute("SELECT * FROM guilds WHERE id = (?)", [str(guild.id)]).fetchall()
            if guildentries == []:
                await addGuild(guild.id)
    else: #Guilds table does not yet exist
        cur.execute('''CREATE TABLE guilds
                    (id, updates_channel, UNIQUE(id))''')
        for guild in guilds:
            guildentries = cur.execute("SELECT * FROM guilds WHERE id = (?)", [str(guild.id)]).fetchall()
            if guildentries == []:
                await addGuild(guild.id)

    cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='mods' ''')
    if cur.fetchone()[0]==1: #Mods table already exists.
        return await checkUpdates()
    else: #Mods table does not yet exist - download full database and create database.
        url = "https://mods.factorio.com/api/mods?page_size=max"
        mods = await getMods(url)
        cur.execute('''CREATE TABLE mods
                (name, release_date, title, owner, version, UNIQUE(name))''')
        cur.executemany("INSERT OR IGNORE INTO mods VALUES (?, ?, ?, ?, ?)", mods)
        con.commit()


async def addGuild(guildID: int):
    cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?)", (str(guildID), None))
    con.commit()

async def removeGuild(guildID: int):
    cur.execute("DELETE FROM guilds WHERE id = (?)", [str(guildID)])
    con.commit()

async def setChannel(guildID: int, channelID: int):
    cur.execute("UPDATE guilds SET updates_channel = (?) WHERE id = (?)", [str(channelID), str(guildID)])
    con.commit()

async def checkUpdates():
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
            mods = await getMods(url)
        except ConnectionError:
            break
        updatedmods = await compareMods(mods)
        if updatedmods != []:
            updatelist += updatedmods
        i += 1
        if len(updatedmods) != 10:
            modupdated = False
    return updatelist

async def getMods(url: str) -> list:
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

async def compareMods(mods: list) -> list:
    """
    Compares mods in list to entries stored in database. Sends list of updated mods to messager. 

    Returns a list of [name, release date, title, owner, version], tag
    """
    updatedmods = []
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

async def make_safe(string: str) -> str:
    """
    Escapes formatting to avoid unwanted behaviour in Discord messages.
    """
    return string.replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "@​\u200b")

async def getThumbnail(name: str) -> str:
    """
    Finds the thumbnail for the specified mods.

    Returns either the URL or None if no thumbnail exists or the connection fails.
    """
    url = f"https://mods.factorio.com/api/mods/{name}"
    response = requests.get(url)
    if response.status_code == 200:
        thumbnailraw = response.json()["thumbnail"]
        if thumbnailraw != "/assets/.thumb.png":
            thumbnailURL = "https://assets-mod.factorio.com" + thumbnailraw
            return thumbnailURL
        else:
            return None
    else:
        return None

async def getChannels() -> list:
    """
    Gets and returns a list of all set channel IDs
    """
    channels = cur.execute("SELECT updates_channel FROM guilds WHERE updates_channel IS NOT NULL").fetchall()
    return channels

async def main():
    """
    Executed when this file is run. Will run through all functions for testing purposes.
    """
    updatelist = await firstStart()
    if updatelist:
        for mod, tag in updatelist:
            name = mod[0]
            title = mod[2]
            owner = mod[3]
            version = mod[4]
            thumbnail = getThumbnail(name)
            print(title, owner, version, thumbnail)

if __name__ == "__main__":
    main()