import sqlite3, json
from pathlib import Path
from datetime import datetime, timedelta
DB=Path(__file__).resolve().parents[1]/"data"/"microsafe.db"; DB.parent.mkdir(exist_ok=True)
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    with conn() as c: c.executescript('''CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY,batch_id TEXT UNIQUE,product TEXT,quantity REAL,packed_at TEXT,ph REAL,aw REAL,packaging TEXT,created_at TEXT,is_synthetic INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,batch_id TEXT,at TEXT,temp REAL,humidity REAL); CREATE TABLE IF NOT EXISTS assessments(id INTEGER PRIMARY KEY,batch_id TEXT,kind TEXT,payload TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,batch_id TEXT,kind TEXT,detail TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS lab_results(id INTEGER PRIMARY KEY,batch_id TEXT,organism TEXT,result TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS synthetic_examples(id INTEGER PRIMARY KEY,features TEXT,label INTEGER,shelf_days REAL,is_synthetic INTEGER DEFAULT 1);''')
def event(c,bid,kind,detail): c.execute("INSERT INTO events(batch_id,kind,detail,created_at) VALUES(?,?,?,?)",(bid,kind,detail,datetime.now().isoformat(timespec='minutes')))
def add_batch(product,quantity,packed_at,ph,aw,packaging,is_synthetic=False,batch_id=None):
    with conn() as c:
        year=datetime.now().year; n=c.execute("SELECT COUNT(*) FROM batches WHERE batch_id LIKE ?",(f"BT-{year}-%",)).fetchone()[0]+1; bid=batch_id or f"BT-{year}-{n:04d}"
        c.execute("INSERT INTO batches(batch_id,product,quantity,packed_at,ph,aw,packaging,created_at,is_synthetic) VALUES(?,?,?,?,?,?,?,?,?)",(bid,product,quantity,str(packed_at),ph,aw,packaging,datetime.now().isoformat(timespec='minutes'),int(is_synthetic))); event(c,bid,"Registration",f"{product} · {quantity:g} kg · packed {packed_at}")
    return bid
def add_log(bid,at,temp,humidity):
    with conn() as c: c.execute("INSERT INTO logs(batch_id,at,temp,humidity) VALUES(?,?,?,?)",(bid,str(at),temp,humidity)); event(c,bid,"Storage log",f"{temp:g} °C, {humidity:g}% RH")
def list_batches():
    with conn() as c: return [dict(x) for x in c.execute("SELECT * FROM batches ORDER BY id DESC")]
def get_batch(bid):
    with conn() as c: return dict(c.execute("SELECT * FROM batches WHERE batch_id=?",(bid,)).fetchone())
def get_logs(bid):
    with conn() as c: return [dict(x) for x in c.execute("SELECT * FROM logs WHERE batch_id=? ORDER BY at",(bid,))]
def save_assessment(bid,kind,payload):
    with conn() as c: c.execute("INSERT INTO assessments(batch_id,kind,payload,created_at) VALUES(?,?,?,?)",(bid,kind,json.dumps(payload),datetime.now().isoformat(timespec='minutes'))); event(c,bid,kind,json.dumps(payload,ensure_ascii=False))
def save_lab(bid,organism,result):
    with conn() as c: c.execute("INSERT INTO lab_results(batch_id,organism,result,created_at) VALUES(?,?,?,?)",(bid,organism,result,datetime.now().isoformat(timespec='minutes'))); event(c,bid,"Lab result",f"{organism}: {result}")
def timeline(bid):
    with conn() as c: return [dict(x) for x in c.execute("SELECT kind,detail,created_at FROM events WHERE batch_id=? ORDER BY created_at",(bid,))]
def seed_demo():
    if list_batches(): return
    now=datetime.now(); ids=[add_batch('Apple',20,now-timedelta(hours=5),3.8,.97,'Sealed',True),add_batch('Apple',15,now-timedelta(hours=8),3.9,.97,'Sealed',True),add_batch('Banana',12,now-timedelta(hours=3),5.0,.98,'Vented',True)]
    for bid,temps in zip(ids,[[4,4,4],[12,12,18,12],[6,7,8]]):
        for j,t in enumerate(temps): add_log(bid,now-timedelta(hours=len(temps)-j),t,75)
