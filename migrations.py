import sqlite3

def upgradetov2():
    print("Upgraded to v2")

migrations = {2: upgradetov2,}

def migrate(old_version, current_version):
    for migration in migrations:
        if migration > old_version and migration <= current_version:
            migrations[migration]()


# with sqlite3.connect("mods.db") as con:
#     cur = con.cursor()

