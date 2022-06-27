import sqlite3

def executeSQL(query: str, **kwargs):
    values = kwargs.get("values")
    action = kwargs.get("action")
    if type(values) != tuple and values is not None:
        raise TypeError("values must be a tuple")
    databaseFile = "./db/orders.db"
    con = sqlite3.connect(databaseFile, timeout=10)
    cur = con.cursor()
    if values:
        cur.execute(query, values)
    else:
        cur.execute(query)
    if action is not None and action.lower() == "fetchone":
        output = cur.fetchone()
    else:
        output = cur.fetchall()
    con.commit()
    con.close()
    return output