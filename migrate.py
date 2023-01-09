import sqlite3
con = sqlite3.connect("mods.db")
cur = con.cursor()

cur.execute("DROP TABLE mods")
con.commit()