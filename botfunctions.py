import requests

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"

def getMods():
    """
    Grabs the list of all mods from the API page and filters out the relevant entries. Returns a list of mods.
    """
    url = "https://mods.factorio.com/api/mods?page_size=max"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json()['results']
        mods = {
            mod['name']: {
                'release_date': mod['latest_release']['released_at'],
                'title': mod['title'],
                'owner': mod['owner'],
                'version': mod['latest_release']['version'],
            }
            for mod in results if mod.get('latest_release') is not None
        }
        return mods
    else:
        return None

def checkUpdates(previous_mods, current_mods):
    """
    Compares the previous mod list to the current one. Returns a list of updated and new mods.
    """
    updated = {}
    for name, mod in current_mods.items():
        if name in previous_mods:
            if previous_mods[name]['release_date'] != mod['release_date']:
                mod['update'] = True
                updated[name] = mod
        else:
            mod['update'] = False
            updated[name] = mod
    return updated or None

def make_safe(string):
    return string.replace("_", "\_").replace("*", "\*").replace("~","\~").replace("@", "\@")

def singleMessageLine(name, mod):
    title = make_safe(mod['title'])
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - len(TRIMMED)] + TRIMMED
    owner = make_safe(mod['owner'])
    link = f'<https://mods.factorio.com/mods/{mod["owner"]}/{name}>'.replace(" ", "%20")
    if mod["update"]:
        return f'**Updated mod:** {title} (updated to version: {mod["version"]}); by {owner} - {link}'
    else:
        return f'**New mod:** {title} by {owner} - {link}'

def writeMessage(updated_mods):
    """
    Formats the message to be posted from the list of updated mods. Returns a formatted, discord-ready message.
    """
    return '\n'.join([
        singleMessageLine(name, mod)
        for name, mod in updated_mods.items()
    ])

def main():
    """
    Executed when this file is run. Will run through all functions for testing purposes.
    """
    import time
    from collections import deque
    modLists = deque([], 2)
    modLists.append(getMods())
    time.sleep(60)
    while True:
        modLists.append(getMods())
        updatedList = checkUpdates(modLists[0], modLists[1])
        if updatedList is not None:
            print(writeMessage(updatedList))
        else: print(f"{time.asctime()}: No updates")
        time.sleep(60)

if __name__ == "__main__":
    main()