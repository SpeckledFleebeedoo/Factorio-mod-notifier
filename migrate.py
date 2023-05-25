import sqlite3
con = sqlite3.connect("mods.db")
cur = con.cursor()

cur.execute("CREATE TABLE version(current_version)")
con.commit()