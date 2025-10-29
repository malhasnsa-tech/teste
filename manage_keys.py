import os, sqlite3, secrets
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DB_PATH", "app.db")

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def create_key(label="Convite", max_uses=1, days_valid=365):
    con = connect()
    key = "NSA-" + secrets.token_hex(4).upper()
    expires_at = (datetime.utcnow() + timedelta(days=days_valid)).isoformat(timespec="seconds")
    con.execute("INSERT INTO access_keys (key,label,max_uses,used_count,active,expires_at) VALUES (?,?,?,?,?,?)",
                (key, label, max_uses, 0, 1, expires_at))
    con.commit()
    con.close()
    print("Chave criada:", key, "| expira em:", expires_at, "| max_uses:", max_uses, "| label:", label)

def list_keys():
    con = connect()
    rows = con.execute("SELECT * FROM access_keys ORDER BY id DESC").fetchall()
    for r in rows:
        print(dict(r))
    con.close()

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["create","list"])
    ap.add_argument("--label", default="Convite")
    ap.add_argument("--max_uses", type=int, default=1)
    ap.add_argument("--days_valid", type=int, default=365)
    args = ap.parse_args()
    if args.cmd == "create":
        create_key(args.label, args.max_uses, args.days_valid)
    else:
        list_keys()
