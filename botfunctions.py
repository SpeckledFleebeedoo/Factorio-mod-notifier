import requests

def getMods():
    """
    Grabs the list of all mods from the API page and filters out the relevant entries. Returns a list of mods.
    """
    url = "https://mods.factorio.com/api/mods?page_size=max"
    raw = requests.get(url)
    results = raw.json()['results']
    modlist = [{"name":result["name"], "releaseDate":result["latest_release"]["released_at"], "title":result["title"], "owner":result["owner"], "version": result["latest_release"]["version"]} for result in results if result.get("latest_release") != None]
    return modlist

def checkUpdates(previousList, currentList):
    """
    Compares the previous mod list to the current one. Returns a list of updated and new mods.
    """
    previousNames = [mod["name"] for mod in previousList]
    updated = []
    for mod in currentList:
        if mod["name"] in previousNames:
            i = previousNames.index(mod["name"])
            if mod["releaseDate"] != previousList[i]["releaseDate"]:
                updated.append([mod, "u"])
        else: updated.append([mod, "n"])
    if updated != []:
        return updated
    else: 
        return None
        
def writeMessage(updatedMods):
    """
    Formats the message to be posted from the list of updated mods. Returns a formatted, discord-ready message.
    """
    output = ""
    for mod, type in updatedMods:
        mod["title"] = mod["title"].replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "\@")
        owner_formatted = mod["owner"].replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "\@")
        if type == "u":
            output += f'**Updated mod:** {mod["title"]} (updated to version: {mod["version"]}); by {owner_formatted} - <https://mods.factorio.com/mods/{mod["owner"]}/{mod["name"]}>\n'
        if type == "n":
            output += f'**New mod:** {mod["title"]} (updated to version: {mod["version"]}); by {owner_formatted} - <https://mods.factorio.com/mods/{mod["owner"]}/{mod["name"]}>\n'
    return output

def main():
    """
    Executed when this file is run. Will run through all functions for testing purposes.
    """
    import time
    oldModList = None
    while True:
        if oldModList == None:
            oldModList = getMods()
            time.sleep(60)
        else: 
            newModList = getMods()
            updatedList = checkUpdates(oldModList, newModList)
            oldModList = newModList
            if updatedList is not None:
                print(writeMessage(updatedList))
            else: print(f"{time.asctime()}: No updates")
            time.sleep(60)

if __name__ == "__main__":
    main()