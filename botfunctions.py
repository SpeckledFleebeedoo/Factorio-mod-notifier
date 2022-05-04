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
                    (id, updates_channel, modrole, UNIQUE(id))''')
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

# async def main():
#     """
#     Executed when this file is run. Will run through all functions for testing purposes.
#     """
#     updatelist = await firstStart()
#     if updatelist:
#         for mod, tag in updatelist:
#             name = mod[0]
#             title = mod[2]
#             owner = mod[3]
#             version = mod[4]
#             thumbnail = getThumbnail(name)
#             print(title, owner, version, thumbnail)

# if __name__ == "__main__":
#     main()