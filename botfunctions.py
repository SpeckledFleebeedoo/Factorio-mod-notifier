import requests
import sqlite3

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"
con = sqlite3.connect("mods.db")
cur = con.cursor()

def firstStart():
    """
    Checks if the database already exists.
    Will update database if it exists, or create a new database if not.
    """
    cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='mods' ''')
    if cur.fetchone()[0]==1: #Mods table already exists.
        return checkUpdates()
    else: #Mods table does not yet exist - download full database and create database.
        url = "https://mods.factorio.com/api/mods?page_size=max"
        mods = getMods(url)
        cur.execute('''CREATE TABLE mods
                (name, release_date, title, owner, version, UNIQUE(name))''')
        cur.executemany("INSERT OR IGNORE INTO mods VALUES (?, ?, ?, ?, ?)", mods)
        con.commit()

def checkUpdates():
    """
    Iterates through pages of recently updated mods until unchanged mods are found.
    """
    modupdated = True
    i = 1
    updatelists = []
    while modupdated == True:
        url = f"https://mods.factorio.com/api/mods?page_size=10&page={i}&sort=updated_at&sort_order=desc"
        try:
            mods = getMods(url)
        except ConnectionError:
            break
        updatedmods = compareMods(mods)
        if updatedmods != []:
            updatelists.append(updatedmods)
        i += 1
        if len(updatedmods) != 10:
            modupdated = False
    return updatelists

def getMods(url):
    """
    Grabs the list of all mods from the API page and filters out the relevant entries. 
    Returns a list of mods.
    """
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json()['results']
        mods = [[mod["name"], mod["latest_release"]["released_at"], mod["title"], mod["owner"], mod["latest_release"]["version"]] for mod in results if mod.get('latest_release') is not None]
        return mods
    else:
        raise ConnectionError("Failed to retrieve mod list")

def compareMods(mods):
    """
    Compares mods in list to entries stored in database. Sends list of updated mods to messager. 
    Returns list of updated mods.
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

def make_safe(string):
    return string.replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "\@")

def singleMessageLine(name, title, owner, version, tag):
    title = make_safe(title)
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - len(TRIMMED)] + TRIMMED
    owner = make_safe(owner)
    link = f'<https://mods.factorio.com/mods/{owner}/{name}>'.replace(" ", "%20")
    if tag == "u":
        return f'**Updated mod:** {title} (updated to version: {version}); by {owner} - {link}'
    else:
        return f'**New mod:** {title} by {owner} - {link}'

def writeMessage(updated_mods):
    """
    Formats the message to be posted from the list of updated mods. Returns a formatted, discord-ready message.
    """
    lines = []
    for mod, tag in updated_mods:
        name = mod[0]
        title = mod[2]
        owner = mod[3]
        version = mod[4]
        lines.append(singleMessageLine(name, title, owner, version, tag))
    return '\n'.join(lines)

def main():
    """
    Executed when this file is run. Will run through all functions for testing purposes.
    """
    firstStart()

if __name__ == "__main__":
    main()