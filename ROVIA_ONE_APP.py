# ============================================================
# ROVIA ONE APP — GOM 13 MODULE CODE CŨ VÀO 1 APP DUY NHẤT
# Mục tiêu: GIỮ LUỒNG/chức năng cũ, chỉ đổi cách hiển thị thành
# một ứng dụng SPA: bấm chọn -> chuyển màn hình bên trong app.
# ============================================================

import sqlite3, hashlib, math, json, threading, time, requests
from datetime import datetime

ROVIA_HEADERS = {"User-Agent": "ROVIA-Smart-Mobility/1.0 (Colab demo)"}
from flask import Flask, request, jsonify, render_template_string

APP = Flask(__name__)
DB = "rovia_one_app.db"

# ---------------- DATABASE ----------------
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
        email TEXT, password TEXT NOT NULL,
        role TEXT DEFAULT 'customer', points INTEGER DEFAULT 135,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS trips(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        pickup TEXT, destination TEXT, distance REAL, duration REAL,
        route_type TEXT, vehicle TEXT, driver_id INTEGER,
        status TEXT, total INTEGER, payment TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ratings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id INTEGER,
        rating REAL, comment TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS vouchers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT,
        points_cost INTEGER, value INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS rewards_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        title TEXT, points INTEGER, created_at TEXT
    )""")
    # Demo account used by the original code
    demo_hash = hashlib.sha256("123456".encode()).hexdigest()
    c.execute("""INSERT OR IGNORE INTO users
        (id,name,phone,email,password,role,points,created_at)
        VALUES(1,?,?,?,?,?,?,?)""",
        ("Khách hàng Demo","0900000000","demo@rovia.ai",demo_hash,
         "customer",135,datetime.now().isoformat()))
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("""INSERT OR IGNORE INTO users
        (id,name,phone,email,password,role,points,created_at)
        VALUES(2,?,?,?,?,?,?,?)""",
        ("ROVIA Admin","0900000099","admin@rovia.ai",admin_hash,
         "admin",0,datetime.now().isoformat()))
    vouchers = [("Giảm 5.000đ",50,5000),("Giảm 10.000đ",90,10000),
                ("Ưu đãi ROVIA Plus",150,0),("Voucher đặc biệt",250,20000)]
    for v in vouchers:
        c.execute("INSERT OR IGNORE INTO vouchers(title,points_cost,value) VALUES(?,?,?)",v)
    c.commit(); c.close()

init_db()

# ---------------- DEMO DATA FROM OLD MODULES ----------------
DRIVERS = [
    {"id":1,"name":"Nguyễn Minh Anh","gender":"Nữ","rating":4.9,"trips":1234,"vehicle":"ROVIA Bike","plate":"59A1-12345","online":True,"experience":"5 năm"},
    {"id":2,"name":"Trần Quốc Bảo","gender":"Nam","rating":4.8,"trips":980,"vehicle":"ROVIA Bike","plate":"59A2-23456","online":True,"experience":"4 năm"},
    {"id":3,"name":"Lê Hoàng Nam","gender":"Nam","rating":4.7,"trips":756,"vehicle":"ROVIA Bike","plate":"59A3-34567","online":True,"experience":"3 năm"},
    {"id":4,"name":"Phạm Ngọc Linh","gender":"Nữ","rating":4.9,"trips":1100,"vehicle":"ROVIA Bike","plate":"59A4-45678","online":True,"experience":"5 năm"},
]

# ---------------- FUZZY 2.11: 6 INPUTS / 20 RULES ----------------
def fuzzy_level(x, a, b, c):
    if x <= a: return 0.0
    if x < b: return (x-a)/(b-a)
    if x <= c: return 1.0
    if c < x < c+(c-b): return max(0.0, 1-(x-c)/(c-b))
    return 0.0

def fuzzy_price_points(distance, traffic, demand, weather, rating, punctuality):
    # Textbook membership ranges preserved. Numeric output mapping is an implementation choice.
    d_short=max(0, min(1,(3-distance)/3))
    d_medium=max(0, min(1, 1-abs(distance-5)/3))
    d_long=max(0, min(1, 1-abs(distance-10)/5))
    d_far=max(0, min(1, (distance-15)/10))
    t_low=max(0, min(1,(30-traffic)/30)); t_med=max(0,min(1,1-abs(traffic-45)/25)); t_high=max(0,min(1,(traffic-60)/40))
    dem_low=max(0,min(1,(30-demand)/30)); dem_med=max(0,min(1,1-abs(demand-45)/25)); dem_high=max(0,min(1,(demand-60)/40))
    good_weather = 1 if weather=="Tốt" else 0
    med_weather = 1 if weather=="Trung bình" else 0
    bad_weather = 1 if weather=="Xấu" else 0
    r_good=max(0,min(1,(rating-3.5)/1.5)); r_med=max(0,min(1,1-abs(rating-3)/1)); r_bad=max(0,min(1,(2.5-rating)/1.5))
    early=max(0,min(1,(punctuality-70)/30)); ontime=max(0,min(1,1-abs(punctuality-60)/20)); late=max(0,min(1,(50-punctuality)/50))
    price_rules=[
      d_short*t_low*dem_low, d_short*t_med*dem_high, d_medium*t_high*dem_high,
      d_long*t_med*good_weather, d_long*t_high*bad_weather, d_far*t_high*dem_high,
      d_medium*t_low*dem_low, d_short*t_high*bad_weather, d_far*bad_weather,
      d_medium*t_med*med_weather]
    price=max(0.0, min(1.0,(sum(r*(i+1) for i,r in enumerate(price_rules))/max(0.01,sum(price_rules)))/10))
    if price < .25: price_label="Thấp"
    elif price < .50: price_label="Trung bình"
    elif price < .75: price_label="Cao"
    else: price_label="Rất cao"
    point_rules=[r_good*early,r_med*ontime,r_bad*late,d_long*t_high*ontime,r_med*t_med*r_good,
                 r_bad*late,d_far*bad_weather*r_good,d_short*r_med*ontime,d_long*t_high*late,d_medium*med_weather*r_good]
    pts=max(point_rules) if point_rules else 0
    if pts>.65: point_label="Cao"
    elif pts>.35: point_label="Trung bình"
    elif pts>.1: point_label="Ít"
    else: point_label="Không có"
    return price_label, point_label

# ---------------- API ----------------
@APP.post('/api/register')
def register():
    d=request.get_json(force=True)
    name=(d.get('name') or '').strip(); phone=(d.get('phone') or '').strip(); pw=d.get('password') or ''
    if not name or not phone or not pw: return jsonify(ok=False,error='Vui lòng nhập đủ thông tin.'),400
    c=db()
    try:
        c.execute("INSERT INTO users(name,phone,email,password,created_at) VALUES(?,?,?,?,?)",
                  (name,phone,d.get('email',''),hashlib.sha256(pw.encode()).hexdigest(),datetime.now().isoformat()))
        c.commit(); uid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        return jsonify(ok=True,user={'id':uid,'name':name,'phone':phone,'role':'customer','points':135})
    except sqlite3.IntegrityError:
        return jsonify(ok=False,error='Số điện thoại đã tồn tại.'),409
    finally: c.close()

@APP.post('/api/login')
def login():
    d=request.get_json(force=True); phone=d.get('phone','').strip(); pw=d.get('password','')
    c=db(); row=c.execute('SELECT * FROM users WHERE phone=?',(phone,)).fetchone(); c.close()
    if not row or row['password'] != hashlib.sha256(pw.encode()).hexdigest():
        return jsonify(ok=False,error='Số điện thoại hoặc mật khẩu không đúng.'),401
    return jsonify(ok=True,user=dict(row))

def rovia_geocode(address):
    if not address or not address.strip():
        return None
    q = address.strip()
    queries = [q, q + ", Việt Nam"]
    if "ueh mekong" in q.lower():
        queries.insert(0, "UEH Mekong, Vĩnh Long, Việt Nam")
    for query in queries:
        try:
            r = requests.get("https://nominatim.openstreetmap.org/search", params={
                "q": query, "format": "jsonv2", "limit": 5,
                "countrycodes": "vn", "addressdetails": 1
            }, headers=ROVIA_HEADERS, timeout=15)
            if r.ok and r.json():
                x = r.json()[0]
                return {"lat":float(x["lat"]),"lon":float(x["lon"]),
                        "display_name":x.get("display_name", q),
                        "source":"OpenStreetMap Nominatim",
                        "address":x.get("address",{})}
        except Exception:
            pass
        time.sleep(.35)
    return None

def rovia_suggest(query, lat=None, lon=None):
    if not query or len(query.strip()) < 2:
        return []
    params={"q":query.strip(),"format":"jsonv2","limit":8,"countrycodes":"vn","addressdetails":1}
    if lat is not None and lon is not None:
        # Bias results around the current point without pretending this is a hard radius.
        params.update({"lat":lat,"lon":lon})
    try:
        r=requests.get("https://nominatim.openstreetmap.org/search",params=params,headers=ROVIA_HEADERS,timeout=15)
        if not r.ok: return []
        out=[]
        for x in r.json():
            out.append({"name":x.get("display_name","")[:180],"lat":float(x["lat"]),"lon":float(x["lon"]),"address":x.get("address",{})})
        return out
    except Exception:
        return []

def rovia_route(lat1,lon1,lat2,lon2):
    url=f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    r=requests.get(url,params={"overview":"full","geometries":"geojson","alternatives":"true","steps":"true"},headers=ROVIA_HEADERS,timeout=30)
    r.raise_for_status(); data=r.json()
    if data.get("code")!="Ok": raise RuntimeError("OSRM không tìm được tuyến đường.")
    return [{"distance_km":round(x["distance"]/1000,2),"duration_min":round(x["duration"]/60,1),"geometry":x["geometry"],"steps":x.get("legs",[{}])[0].get("steps",[])} for x in data.get("routes",[])]

def route_fare(distance_km, vehicle="ROVIA Bike"):
    if vehicle == "ROVIA Car":
        base=35000; included=2.0; extra=7500
    else:
        base=26000; included=3.5; extra=4500
    extra_km=max(0.0,distance_km-included)
    extra_fee=int(round(extra_km*extra,-2))
    total=int(round(base+extra_fee,-2))
    return {
        "base":base,
        "included_km":included,
        "extra_km":round(extra_km,2),
        "extra_fee":extra_fee,
        "total":total
    }

def route_price(distance_km, vehicle="ROVIA Bike"):
    return route_fare(distance_km,vehicle)["total"]

@APP.post('/api/suggest')
def suggest():
    d=request.get_json(force=True)
    return jsonify(ok=True,results=rovia_suggest(d.get('q',''),d.get('lat'),d.get('lon')))

@APP.post('/api/nearby')
def nearby():
    d=request.get_json(force=True)
    lat=d.get('lat'); lon=d.get('lon')
    if lat is None or lon is None:
        return jsonify(ok=False,error='Thiếu GPS để tìm địa điểm gần đây.'),400
    try:
        # Dữ liệu địa điểm/đường thật từ OpenStreetMap Overpass.
        query=f'''
        [out:json][timeout:12];
        (
          way(around:1200,{float(lat)},{float(lon)})["highway"]["name"];
          nwr(around:1200,{float(lat)},{float(lon)})["amenity"]["name"];
          nwr(around:1200,{float(lat)},{float(lon)})["shop"]["name"];
          nwr(around:1200,{float(lat)},{float(lon)})["tourism"]["name"];
        );
        out center tags;
        '''
        r=requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers=ROVIA_HEADERS,
            timeout=20
        )
        r.raise_for_status()
        items=[]
        seen=set()
        for x in r.json().get("elements",[]):
            tags=x.get("tags",{})
            name=tags.get("name")
            if not name:
                continue
            if x.get("type")=="node":
                la=x.get("lat"); lo=x.get("lon")
            else:
                center=x.get("center",{})
                la=center.get("lat"); lo=center.get("lon")
            if la is None or lo is None:
                continue
            road=tags.get("addr:street") or tags.get("street") or tags.get("highway")
            kind=tags.get("amenity") or tags.get("shop") or tags.get("tourism") or "Đường"
            key=(name,round(float(la),5),round(float(lo),5))
            if key in seen:
                continue
            seen.add(key)
            dist=math.sqrt(((float(la)-float(lat))*111)**2+((float(lo)-float(lon))*111*math.cos(math.radians(float(lat))))**2)
            items.append({
                "name":name,
                "lat":float(la),"lon":float(lo),
                "type":"Đường" if tags.get("highway") else kind,
                "road":road or "",
                "distance_km":round(dist,2)
            })
        items.sort(key=lambda x:x["distance_km"])
        return jsonify(ok=True,results=items[:12],source="OpenStreetMap Overpass")
    except Exception:
        return jsonify(ok=True,results=[],source="OpenStreetMap Overpass")

@APP.post('/api/route')
def route():
    d=request.get_json(force=True)
    pickup=str(d.get('pickup','')).strip()
    dest=str(d.get('destination','')).strip()
    vehicle=d.get('vehicle','ROVIA Bike')
    try:
        if d.get('pickup_lat') is not None and d.get('pickup_lon') is not None:
            p={
                "lat":float(d['pickup_lat']),
                "lon":float(d['pickup_lon']),
                "display_name":pickup or "Vị trí hiện tại",
                "source":"GPS / OpenStreetMap",
                "address":{}
            }
        else:
            p=rovia_geocode(pickup)
        if d.get('destination_lat') is not None and d.get('destination_lon') is not None:
            q={
                "lat":float(d['destination_lat']),
                "lon":float(d['destination_lon']),
                "display_name":dest,
                "source":"OpenStreetMap",
                "address":{}
            }
        else:
            q=rovia_geocode(dest)
        if not p: return jsonify(ok=False,error=f"Không tìm thấy điểm đi: {pickup}"),400
        if not q: return jsonify(ok=False,error=f"Không tìm thấy điểm đến: {dest}"),400
        routes=rovia_route(p['lat'],p['lon'],q['lat'],q['lon'])
        if not routes: return jsonify(ok=False,error='Không tìm được tuyến đường thực tế.'),400
        labels=['Nhanh nhất','Tuyến thay thế 1','Tuyến thay thế 2']
        out=[]
        for i,x in enumerate(routes[:3]):
            fare=route_fare(x['distance_km'],vehicle)
            out.append({
                "type":labels[i],
                "distance":x['distance_km'],
                "duration":x['duration_min'],
                "price":fare["total"],
                "fare":fare,
                "geometry":x['geometry'],
                "steps":x['steps']
            })
        return jsonify(
            ok=True,pickup=p,destination=q,routes=out,
            data_source="OpenStreetMap + OSRM",
            fare_source="ROVIA fare formula"
        )
    except Exception as e:
        return jsonify(ok=False,error=f"Không lấy được dữ liệu bản đồ/tuyến thực: {e}"),502

@APP.post('/api/weather')
def weather():
    d=request.get_json(force=True); lat=d.get('lat'); lon=d.get('lon')
    if lat is None or lon is None: return jsonify(ok=False,error='Thiếu tọa độ'),400
    try:
        r=requests.get('https://api.open-meteo.com/v1/forecast',params={"latitude":lat,"longitude":lon,"current":"temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m","timezone":"auto"},timeout=15)
        r.raise_for_status(); cur=r.json()['current']; code=int(cur.get('weather_code',0) or 0)
        label='Trời quang'
        if code in (1,2,3): label='Mây / nhiều mây'
        elif code in (51,53,55,61,63,65,80,81,82): label='Mưa'
        elif code in (95,96,99): label='Dông'
        return jsonify(ok=True,current=cur,label=label)
    except Exception as e: return jsonify(ok=False,error=str(e)),502

@APP.post('/api/match')
def match():
    d=request.get_json(force=True)
    pref=d.get('gender','Bất kỳ'); min_rating=float(d.get('rating',0) or 0)
    arr=[x for x in DRIVERS if x['online'] and x['rating']>=min_rating and (pref=='Bất kỳ' or x['gender']==pref)]
    return jsonify(ok=True,drivers=arr or DRIVERS[:2])

@APP.post('/api/trip')
def trip():
    d=request.get_json(force=True); c=db()
    cur=c.execute('INSERT INTO trips(user_id,pickup,destination,distance,duration,route_type,vehicle,driver_id,status,total,payment,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
      (d.get('user_id',1),d.get('pickup',''),d.get('destination',''),d.get('distance',3.01),d.get('duration',3.7),d.get('route_type','Nhanh nhất'),'ROVIA Bike',d.get('driver_id'), 'Đang tìm tài xế',d.get('total',26000),'Chưa thanh toán',datetime.now().isoformat()))
    tid=cur.lastrowid; c.commit(); c.close(); return jsonify(ok=True,trip_id=tid)

@APP.post('/api/pay')
def pay():
    d=request.get_json(force=True); c=db(); c.execute('UPDATE trips SET payment=?,status=? WHERE id=?',(d.get('method','Tiền mặt'),'Đã thanh toán',d.get('trip_id'))); c.commit(); c.close(); return jsonify(ok=True)

@APP.post('/api/rating')
def rating():
    d=request.get_json(force=True); c=db(); c.execute('INSERT INTO ratings(trip_id,rating,comment,created_at) VALUES(?,?,?,?)',(d.get('trip_id'),d.get('rating',5),d.get('comment',''),datetime.now().isoformat())); c.execute('UPDATE trips SET status=? WHERE id=?',('Hoàn thành',d.get('trip_id'))); c.commit(); c.close(); return jsonify(ok=True)

@APP.get('/api/history')
def history():
    c=db(); rows=[dict(x) for x in c.execute('SELECT * FROM trips ORDER BY id DESC LIMIT 10')]; c.close(); return jsonify(ok=True,trips=rows)

@APP.post('/api/fuzzy')
def fuzzy():
    d=request.get_json(force=True)
    p,pts=fuzzy_price_points(float(d.get('distance',3)),float(d.get('traffic',30)),float(d.get('demand',30)),d.get('weather','Tốt'),float(d.get('rating',4.5)),float(d.get('punctuality',80)))
    return jsonify(ok=True,price=p,points=pts)

# ---------------- ONE APP HTML ----------------
HTML=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ROVIA — AI Smart Mobility</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f4f7f5;color:#17202a}.app{height:100vh;display:flex;overflow:hidden}.side{width:245px;background:#101827;color:#fff;padding:20px 14px;display:flex;flex-direction:column}.logo{font-size:28px;font-weight:900;color:#00b14f;padding:4px 12px}.tag{font-size:11px;color:#94a3b8;padding:0 12px 22px}.nav{display:flex;flex-direction:column;gap:6px}.nav button{border:0;background:transparent;color:#cbd5e1;text-align:left;padding:12px;border-radius:10px;cursor:pointer;font-size:14px}.nav button:hover,.nav button.active{background:#00b14f;color:#fff}.main{flex:1;min-width:0;display:flex;flex-direction:column}.top{height:68px;background:#fff;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;padding:0 24px}.userpill{background:#f1f5f9;border-radius:20px;padding:9px 14px;font-size:13px}.content{flex:1;overflow:auto;padding:22px}.view{display:none;animation:in .22s ease}.view.active{display:block}@keyframes in{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}.hero{background:linear-gradient(135deg,#00b14f,#008d40);color:#fff;border-radius:20px;padding:28px;margin-bottom:18px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.card{background:#fff;border-radius:16px;padding:18px;box-shadow:0 4px 18px #0f172a0d;border:1px solid #edf0f2}.card.click{cursor:pointer}.card.click:hover{transform:translateY(-2px);box-shadow:0 8px 25px #0f172a14}.label{font-size:12px;color:#64748b;margin-bottom:6px}.input,select,textarea{width:100%;padding:12px;border:1px solid #dbe2e8;border-radius:10px;background:#fff}.btn{border:0;border-radius:10px;padding:12px 16px;background:#00b14f;color:#fff;font-weight:700;cursor:pointer}.btn.secondary{background:#e8f4ed;color:#087a39}.btn.dark{background:#17202a}.btn.red{background:#dc2626}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.space{height:12px}.big{font-size:30px;font-weight:900}.muted{color:#64748b}.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:#e8f7ef;color:#087a39;font-size:12px;font-weight:700}.route{border:2px solid #e5e7eb;border-radius:14px;padding:14px;cursor:pointer}.route.sel{border-color:#00b14f;background:#f0fff6}.driver{display:flex;gap:14px;align-items:center}.avatar{width:50px;height:50px;border-radius:50%;background:#e7f7ee;display:grid;place-items:center;font-size:24px}.map{height:320px;border-radius:16px;overflow:hidden}.live-map{height:440px;border-radius:16px;overflow:hidden}.live-status{display:flex;gap:8px;flex-wrap:wrap}.status-pill{padding:8px 12px;border-radius:999px;background:#eef2f7;font-size:12px;font-weight:700}.status-pill.on{background:#e8f7ef;color:#087a39}.stepbar{display:flex;gap:7px;overflow:auto;padding-bottom:14px}.stepbar span{white-space:nowrap;padding:7px 10px;border-radius:999px;background:#e5e7eb;color:#64748b;font-size:11px}.stepbar span.on{background:#00b14f;color:#fff}.bottom{display:none}.toast{position:fixed;right:22px;bottom:22px;background:#111827;color:#fff;padding:13px 17px;border-radius:12px;display:none;z-index:99}.auth{height:100vh;display:none;place-items:center;background:linear-gradient(135deg,#005d2b,#00b14f)}.authbox{width:min(440px,92vw);background:#fff;padding:30px;border-radius:22px}.hidden{display:none!important}@media(max-width:900px){.side{display:none}.grid,.grid2{grid-template-columns:1fr}.bottom{display:flex;position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #ddd;z-index:50}.bottom button{flex:1;border:0;background:#fff;padding:10px;font-size:11px}.content{padding-bottom:80px}}
.suggestbox{position:absolute;left:0;right:0;top:74px;background:#fff;border:1px solid #dbe2e8;border-radius:12px;box-shadow:0 10px 30px #0f172a18;z-index:9999;overflow:hidden;pointer-events:auto}.suggestitem{display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 12px;cursor:pointer;font-size:13px;border:0;border-bottom:1px solid #eef2f5;background:#fff;color:#1f2937;pointer-events:auto}.suggestitem:hover{background:#f0fff6}.suggestempty{padding:10px;color:#64748b;font-size:12px}</style></head><body>
<div id="auth" class="auth"><div class="authbox"><h1 style="color:#00b14f">🚗 ROVIA</h1><p class="muted">AI-POWERED SMART MOBILITY</p><div id="loginBox"><h2>Đăng nhập</h2><input id="lphone" class="input" placeholder="Số điện thoại"><div class="space"></div><input id="lpw" type="password" class="input" placeholder="Mật khẩu"><div class="space"></div><button class="btn" style="width:100%" onclick="login()">Đăng nhập</button><div class="space"></div><button class="btn secondary" style="width:100%" onclick="toggleAuth()">Tạo tài khoản</button><p class="muted" style="font-size:12px">Demo: 0900000000 / 123456</p></div><div id="regBox" class="hidden"><h2>Tạo tài khoản</h2><input id="rname" class="input" placeholder="Họ tên"><div class="space"></div><input id="rphone" class="input" placeholder="Số điện thoại"><div class="space"></div><input id="remail" class="input" placeholder="Email"><div class="space"></div><input id="rpw" type="password" class="input" placeholder="Mật khẩu"><div class="space"></div><button class="btn" style="width:100%" onclick="register()">Tạo tài khoản</button><div class="space"></div><button class="btn secondary" style="width:100%" onclick="toggleAuth()">Đã có tài khoản</button></div></div></div>
<div id="app" class="app hidden"><aside class="side"><div class="logo">🚗 ROVIA</div><div class="tag">AI-POWERED SMART MOBILITY</div><div class="nav" id="nav"><button data-v="home">🏠 Trang chủ</button><button data-v="booking">🛵 Đặt chuyến</button><button data-v="needs">🎒 Nhu cầu</button><button data-v="route">🗺️ Tuyến đường</button><button data-v="match">🧠 Smart Matching</button><button data-v="live">📡 Theo dõi chuyến</button><button data-v="payment">💳 Thanh toán</button><button data-v="rating">⭐ Đánh giá</button><button data-v="rewards">🎁 Rewards</button><button data-v="safety">🛡️ Safety</button><button data-v="ai">🤖 Fuzzy AI</button><button data-v="driver">🚗 Driver</button><button data-v="admin">👨‍💼 Admin</button></div></aside><main class="main"><header class="top"><b id="title">Trang chủ</b><div class="userpill" id="userpill">Khách</div></header><div class="content">
<div class="stepbar" id="stepbar"></div>
<section id="home" class="view active"><div class="hero"><h1>ROVIA</h1><p>Một ứng dụng smart mobility — chọn nhu cầu và đi từng bước ngay trong cùng một màn hình.</p><button class="btn" onclick="go('booking')">🚀 Đặt chuyến ngay</button></div><div class="grid"><div class="card click" onclick="go('booking')"><div class="big">🛵</div><h3>Đặt chuyến</h3><p class="muted">Điểm đón, điểm đến, phương tiện.</p></div><div class="card click" onclick="go('route')"><div class="big">🗺️</div><h3>Smart Route</h3><p class="muted">Nhanh · An toàn · Tiết kiệm.</p></div><div class="card click" onclick="go('safety')"><div class="big">🛡️</div><h3>Safety Center</h3><p class="muted">SOS, chia sẻ chuyến, xác minh.</p></div></div></section>
<section id="booking" class="view"><div class="card"><h2>🛵 Đặt chuyến</h2><div class="grid2"><div style="position:relative"><div class="label">Điểm đón</div><input id="pickup" class="input" autocomplete="off" placeholder="Nhập tên đường / địa điểm..."><div id="pickupSuggest" class="suggestbox"></div><div class="row" style="margin-top:8px"><button class="btn secondary" onclick="useCurrentLocation()">📍 Vị trí hiện tại</button><button class="btn secondary" onclick="suggestNearby('pickup')">⭐ Gợi ý gần đây</button></div></div><div style="position:relative"><div class="label">Điểm đến</div><input id="destination" class="input" autocomplete="off" placeholder="Ví dụ: Vincom Plaza..."><div id="destinationSuggest" class="suggestbox"></div><div class="row" style="margin-top:8px"><button class="btn secondary" onclick="suggestNearby('destination')">⭐ Gợi ý gần đây</button></div></div></div><div class="space"></div><div class="grid"><div><div class="label">Phương tiện</div><select id="vehicle" class="input"><option>ROVIA Bike</option><option>ROVIA Car</option></select></div><div><div class="label">Kiểu chuyến</div><select id="mode" class="input"><option>Ride</option><option>Family</option><option>Delivery</option><option>Pet</option></select></div><div style="display:flex;align-items:end"><button class="btn" style="width:100%" onclick="calcRoute()">🔎 Tìm tuyến thực →</button></div></div><p class="muted" style="font-size:12px;margin-bottom:0">Gợi ý tên đường/địa điểm dùng OpenStreetMap; tuyến thực tế và khoảng cách dùng OSRM; thời tiết lấy theo tọa độ thực.</p></div></section><section id="needs" class="view"><div class="card"><h2>🎒 Nhu cầu + nhận diện khi gặp tài xế</h2><div class="grid"><label><input type="checkbox" id="child"> 👶 Trẻ em</label><label><input type="checkbox" id="luggage"> 🧳 Hành lý</label><label><input type="checkbox" id="pet"> 🐶 Pet Mode</label><label><input type="checkbox" id="elder"> 👵 Người lớn tuổi</label><label><input type="checkbox" id="rain"> 🧥 Áo mưa</label><label><input type="checkbox" id="charge"> 🔋 Sạc điện thoại</label><label><input type="checkbox" id="water"> 💧 Nước</label><label><input type="checkbox" id="quiet"> 🤫 Chuyến yên tĩnh</label></div><div class="space"></div><div class="grid2"><div><div class="label">Giới tính tài xế</div><select id="gender" class="input"><option>Bất kỳ</option><option>Nữ</option><option>Nam</option></select></div><div><div class="label">Rating tối thiểu</div><select id="minrating" class="input"><option>0</option><option>4.5</option><option>4.8</option><option>4.9</option></select></div></div><div class="space"></div><h3>👋 Dấu hiệu để tài xế nhận ra bạn</h3><div class="grid"><div><div class="label">Màu áo</div><select id="shirtColor" class="input"><option>Đen</option><option>Trắng</option><option>Xanh</option><option>Đỏ</option><option>Vàng</option><option>Khác</option></select></div><div><div class="label">Balo / túi</div><select id="bagType" class="input"><option>Có balo</option><option>Không có balo</option><option>Túi xách</option><option>Vali</option></select></div><div><div class="label">Vật dễ nhận biết</div><input id="meetingItem" class="input" placeholder="Ví dụ: cầm ô vàng"></div></div><div class="space"></div><div class="label">Ghi chú điểm gặp</div><textarea id="meetingNote" class="input" rows="3" placeholder="Ví dụ: đứng trước cổng, gần bảng tên đường..."></textarea><div class="space"></div><button class="btn" onclick="saveNeeds()">Lưu nhu cầu →</button></div></section><section id="route" class="view"><div class="grid2"><div class="card"><h2>🗺️ Bản đồ thực tế / tuyến đường</h2><div id="map" class="map"></div><div class="space"></div><div id="placeInfo" class="muted">Nhập điểm đón và điểm đến để lấy tọa độ, tên đường và tuyến thực tế.</div><div class="space"></div><div class="badge">🌐 Dữ liệu bản đồ: OpenStreetMap · Tuyến: OSRM · Thời tiết: Open-Meteo</div></div><div class="card"><h2>🌦️ Thời tiết tại điểm đi</h2><div class="grid"><div><span class="big" id="weatherTemp">--°</span><br><span class="muted">Nhiệt độ</span></div><div><span class="big" id="weatherHum">--%</span><br><span class="muted">Độ ẩm</span></div><div><span class="big" id="weatherRain">--</span><br><span class="muted">Mưa</span></div></div><div class="space"></div><div class="badge" id="weatherLabel">Đang lấy dữ liệu...</div><p class="muted">Dữ liệu thời tiết lấy theo tọa độ điểm đi.</p></div></div><div class="space"></div><div id="routes" class="grid"></div><div class="space"></div><div id="routeSteps" class="card hidden"><h3>🛣️ Tên đường / các đoạn tuyến</h3><div id="stepsList"></div></div></section><section id="match" class="view"><div class="card"><h2>🧠 Smart Matching 2.0</h2><p class="muted">ROVIA ghép tài xế theo rating, giới tính và nhu cầu chuyến.</p><div id="drivers" class="grid"></div></div></section>
<section id="live" class="view"><div class="hero"><h2>📡 Live Trip / Trip Guardian</h2><p>🚗 Xe đang di chuyển trên <b>tuyến đường thực tế</b>.</p><div class="big" id="liveTime">00:00</div><div class="live-status"><span class="status-pill on" id="driverStatus">🟢 Tài xế đang di chuyển</span><span class="status-pill" id="etaStatus">ETA: -- phút</span><span class="status-pill" id="distanceStatus">Còn: -- km</span></div></div><div class="grid2"><div class="card"><h3>🗺️ Vị trí tài xế</h3><div id="liveMap" class="live-map"></div><p class="muted" id="liveMapNote">🏍️ Xe hiển thị trên chính tuyến OSRM vừa tính. Đây là mô phỏng vị trí GPS; GPS ngoài đời cần app/thiết bị tài xế gửi tọa độ.</p></div><div><div class="card"><b>📍 Lộ trình</b><p id="liveRoute">Chưa có chuyến.</p></div><div class="space"></div><div class="card"><b>🚗 Tài xế</b><p id="liveDriver">Đang chờ.</p><p class="muted" id="liveVehicle">Xe: --</p></div><div class="space"></div><div class="card"><b>👋 Dấu hiệu nhận diện</b><p id="liveMeet">Chưa có.</p></div><div class="space"></div><div class="card"><b>🛡️ Guardian</b><p>Chia sẻ chuyến · SOS · PIN xác minh.</p><button class="btn secondary" onclick="toast('Đã chia sẻ thông tin chuyến')">📤 Chia sẻ chuyến</button></div></div></div><div class="space"></div><button class="btn red" onclick="finishTrip()">🏁 Kết thúc chuyến</button></section><section id="payment" class="view"><div class="grid2"><div class="card"><h2>💳 Payment Center</h2><p>Tiền chuyến: <b id="payTotal">26.000đ</b></p><div class="grid"><button class="btn secondary" onclick="pay('Tiền mặt')">💵 Tiền mặt</button><button class="btn secondary" onclick="pay('Ví điện tử')">📱 Ví điện tử</button><button class="btn secondary" onclick="pay('Ngân hàng')">🏦 Ngân hàng</button><button class="btn secondary" onclick="pay('Thẻ ngân hàng')">💳 Thẻ</button></div></div><div class="card"><h3>📋 Chi tiết</h3><p>Khoảng cách: <span id="billDistance">3.01 km</span></p><p>Thời gian: <span id="billDuration">3.7 phút</span></p><p>Giá cơ bản: <span id="billBase">26.000đ</span></p><p>Phần vượt mức: <span id="billExtra">0đ</span></p><p>Phí dịch vụ: 0đ</p><hr><h2 id="billTotal">26.000đ</h2><div class="badge">Tính theo quãng đường tuyến thực tế</div></div></div></section>
<section id="rating" class="view"><div class="card"><h2>⭐ Post Trip Experience</h2><div class="label">Đánh giá</div><select id="ratingVal" class="input"><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select><div class="space"></div><textarea id="comment" class="input" rows="4" placeholder="Nhận xét chuyến đi..."></textarea><div class="space"></div><button class="btn" onclick="rateTrip()">Gửi đánh giá →</button></div></section>
<section id="rewards" class="view"><div class="grid"><div class="card"><div class="label">Điểm hiện có</div><div class="big" id="points">135</div><span class="badge">Silver</span></div><div class="card"><h3>🎁 Voucher</h3><p>Giảm 5.000đ — 50 điểm</p><p>Giảm 10.000đ — 90 điểm</p><p>ROVIA Plus — 150 điểm</p></div><div class="card"><h3>🔥 Streak</h3><div class="big">4 ngày</div><p class="muted">Chuyến: 18</p></div></div></section>
<section id="safety" class="view"><div class="grid"><div class="card"><h2>🆘 SOS</h2><p>Kích hoạt hỗ trợ khẩn cấp.</p><button class="btn red" onclick="toast('Đã kích hoạt SOS demo')">SOS</button></div><div class="card"><h2>📤 Chia sẻ chuyến</h2><p>Chia sẻ thông tin chuyến cho người thân.</p><button class="btn" onclick="toast('Đã tạo link chia sẻ demo')">Chia sẻ</button></div><div class="card"><h2>🔐 Xác minh</h2><p>Tên tài xế · ảnh · biển số · PIN.</p><button class="btn secondary" onclick="toast('Thông tin xác minh đã hiển thị')">Kiểm tra</button></div></div></section>
<section id="ai" class="view"><div class="card"><h2>🤖 ROVIA AI / Fuzzy Lab</h2><p class="muted">Mô hình GrabBike 2.11: Distance + Traffic + Demand + Weather + Rating + Punctuality.</p><div class="grid"><div><div class="label">Distance (km)</div><input id="fd" class="input" type="number" value="3"></div><div><div class="label">Traffic (%)</div><input id="ft" class="input" type="number" value="30"></div><div><div class="label">Demand (%)</div><input id="fm" class="input" type="number" value="30"></div><div><div class="label">Weather</div><select id="fw" class="input"><option>Tốt</option><option>Trung bình</option><option>Xấu</option></select></div><div><div class="label">Rating</div><input id="fr" class="input" type="number" step="0.1" value="4.5"></div><div><div class="label">Punctuality (%)</div><input id="fp" class="input" type="number" value="80"></div></div><div class="space"></div><button class="btn" onclick="runFuzzy()">Chạy Fuzzy</button><div class="space"></div><div id="fuzzyResult" class="card" style="background:#f6fff9">Chưa chạy.</div></div></section>
<section id="driver" class="view"><div class="card"><h2>🚗 Driver Dashboard</h2><div class="grid"><div><div class="big">🟢</div><p>Online</p></div><div><div class="big">4.9⭐</div><p>Rating</p></div><div><div class="big">1,234</div><p>Chuyến</p></div></div><div class="space"></div><button class="btn" onclick="toast('Đã bật trạng thái nhận chuyến')">Bật nhận chuyến</button></div></section>
<section id="admin" class="view"><div class="card"><h2>👨‍💼 Admin Dashboard</h2><div class="grid"><div class="card"><div class="label">Customers</div><div class="big">1</div></div><div class="card"><div class="label">Drivers online</div><div class="big">4</div></div><div class="card"><div class="label">Trips</div><div class="big" id="adminTrips">0</div></div></div><div class="space"></div><button class="btn" onclick="loadHistory()">Cập nhật dữ liệu</button></div></section>
</div></main></div><div class="bottom"><button onclick="go('home')">🏠<br>Home</button><button onclick="go('booking')">🛵<br>Đặt</button><button onclick="go('live')">📡<br>Trip</button><button onclick="go('rewards')">🎁<br>Rewards</button></div><div id="toast" class="toast"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
let user=null,tripId=null,selectedRoute=null,selectedDriver=null,currentView='home',timerStart=null,map=null,liveMap=null,liveMarker=null,liveLine=null,liveProgress=null,liveTimer=null,liveStep=0;
const order=['home','booking','needs','route','match','live','payment','rating','rewards','safety','ai','driver','admin'];
const names={home:'Trang chủ',booking:'Đặt chuyến',needs:'Nhu cầu chuyến',route:'Tuyến đường + Weather',match:'Smart Matching',live:'Live Trip / Trip Guardian',payment:'Payment Center',rating:'Post Trip Experience',rewards:'Rewards & Loyalty',safety:'Safety Center',ai:'ROVIA AI / Fuzzy Lab',driver:'Driver Dashboard',admin:'Admin Dashboard'};
function toast(x){let t=document.getElementById('toast');t.textContent=x;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}
function toggleAuth(){document.getElementById('loginBox').classList.toggle('hidden');document.getElementById('regBox').classList.toggle('hidden')}
async function login(){let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:lphone.value,password:lpw.value})});let j=await r.json();if(!j.ok)return toast(j.error);user=j.user;startApp()}
async function register(){let r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:rname.value,phone:rphone.value,email:remail.value,password:rpw.value})});let j=await r.json();if(!j.ok)return toast(j.error);user=j.user;startApp()}
function startApp(){document.getElementById('auth').style.display='none';document.getElementById('app').classList.remove('hidden');document.getElementById('userpill').textContent='👤 '+user.name;renderSteps();go('home')}
function renderSteps(){let s=document.getElementById('stepbar');s.innerHTML=order.map((x,i)=>`<span id="sb-${x}">${String(i+1).padStart(2,'0')} ${names[x]}</span>`).join('')}
function go(v){
  currentView=v;
  document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));
  document.getElementById(v).classList.add('active');
  document.getElementById('title').textContent=names[v];
  document.querySelectorAll('#nav button').forEach(b=>b.classList.toggle('active',b.dataset.v===v));
  document.querySelectorAll('#stepbar span').forEach(x=>x.classList.remove('on'));
  let el=document.getElementById('sb-'+v); if(el)el.classList.add('on');
  document.querySelector('.content').scrollTop=0;
  if(v==='route'){
    if(!map)initMap();
    setTimeout(()=>{
      map.invalidateSize(true);
      if(window.routeData) drawRealRoute(window.routeData);
    },180);
  }
  if(v==='live'&&liveMap)setTimeout(()=>liveMap.invalidateSize(true),180);
}
let suggestTimer=null;let currentGPS=null;
async function suggestPlaces(which){
  clearTimeout(suggestTimer);
  suggestTimer=setTimeout(async()=>{
    const el=document.getElementById(which+'Suggest');
    const q=document.getElementById(which).value.trim();
    if(q.length<2){el.replaceChildren();return}
    el.innerHTML='<div class="suggestempty">🔎 Đang tìm địa điểm...</div>';
    try{
      const r=await fetch('/api/suggest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:q,lat:currentGPS?.lat,lon:currentGPS?.lon})});
      const j=await r.json();
      el.replaceChildren();
      const results=j.results||[];
      if(!results.length){
        const empty=document.createElement('div'); empty.className='suggestempty'; empty.textContent='Không có kết quả.'; el.appendChild(empty); return;
      }
      results.forEach((x,idx)=>{
        const item=document.createElement('button');
        item.type='button';
        item.className='suggestitem';
        item.dataset.index=idx;
        item.textContent='📍 '+(x.name||'Địa điểm');
        item.addEventListener('mousedown',e=>e.preventDefault());
        item.addEventListener('click',e=>{
          e.preventDefault(); e.stopPropagation();
          pickSuggestion(which,idx,results);
        });
        el.appendChild(item);
      });
    }catch(e){
      el.replaceChildren();
      const err=document.createElement('div'); err.className='suggestempty'; err.textContent='Không tải được gợi ý. Thử lại nhé.'; el.appendChild(err);
    }
  },350);
}
function pickSuggestion(which,index,results){
  const item=results[index];
  if(!item)return;
  const input=document.getElementById(which);
  const box=document.getElementById(which+'Suggest');
  input.value=item.name||'';
  input.dataset.lat=item.lat||'';
  input.dataset.lon=item.lon||'';
  input.dataset.displayName=item.name||'';
  box.replaceChildren();
  input.dispatchEvent(new Event('change',{bubbles:true}));
  toast('Đã chọn địa điểm ✓');
}
async function suggestNearby(which){
  const el=document.getElementById(which+'Suggest');
  if(!currentGPS){
    el.innerHTML='<div class="suggestempty">📍 Bấm Vị trí hiện tại trước để lấy các đường/địa điểm gần bạn.</div>';
    return;
  }
  el.innerHTML='<div class="suggestempty">📍 Đang lấy đường và địa điểm gần bạn...</div>';
  try{
    const r=await fetch('/api/nearby',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:currentGPS.lat,lon:currentGPS.lon})});
    const j=await r.json(); el.replaceChildren();
    (j.results||[]).forEach(x=>{
      const item=document.createElement('button');
      item.type='button'; item.className='suggestitem';
      item.innerHTML='<b>📍 '+escapeHtml(x.name)+'</b><br><span class="muted">'+escapeHtml(x.type||'Địa điểm')+' · '+x.distance_km+' km'+(x.road?' · '+escapeHtml(x.road):'')+'</span>';
      item.addEventListener('mousedown',e=>e.preventDefault());
      item.addEventListener('click',e=>{
        e.preventDefault(); e.stopPropagation();
        const input=document.getElementById(which);
        input.value=x.name+(x.road?' · '+x.road:'');
        input.dataset.lat=x.lat; input.dataset.lon=x.lon;
        el.replaceChildren(); toast('Đã chọn '+x.name+' ✓');
      });
      el.appendChild(item);
    });
    if(!el.children.length) el.innerHTML='<div class="suggestempty">Không tìm được dữ liệu gần đây.</div>';
  }catch(e){
    el.innerHTML='<div class="suggestempty">Không tải được dữ liệu gần đây.</div>';
  }
}
function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
function useCurrentLocation(){
  if(!navigator.geolocation)return toast('Trình duyệt không hỗ trợ GPS');
  toast('Đang lấy vị trí hiện tại...');
  navigator.geolocation.getCurrentPosition(async pos=>{
    currentGPS={lat:pos.coords.latitude,lon:pos.coords.longitude};
    try{
      let r=await fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat='+currentGPS.lat+'&lon='+currentGPS.lon+'&zoom=18&addressdetails=1',{headers:{'Accept-Language':'vi'}});
      let j=await r.json();
      pickup.value=j.display_name||'Vị trí hiện tại';
      pickup.dataset.lat=currentGPS.lat; pickup.dataset.lon=currentGPS.lon;
      toast('Đã lấy GPS thực tế ✓');
    }catch(e){
      pickup.value='Vị trí hiện tại';
      pickup.dataset.lat=currentGPS.lat; pickup.dataset.lon=currentGPS.lon;
      toast('Đã lấy GPS ✓');
    }
  },()=>toast('Không lấy được GPS. Hãy cho phép Location.'),{enableHighAccuracy:true,timeout:15000,maximumAge:0});
}
document.addEventListener('input',e=>{
  if(e.target&&e.target.id==='pickup')suggestPlaces('pickup');
  if(e.target&&e.target.id==='destination')suggestPlaces('destination');
});
document.addEventListener('click',e=>{
  if(!e.target.closest('.suggestbox')&&!e.target.closest('#pickup')&&!e.target.closest('#destination')){
    document.getElementById('pickupSuggest').replaceChildren();
    document.getElementById('destinationSuggest').replaceChildren();
  }
});
async function calcRoute(){
  if(!pickup.value||!destination.value)return toast('Nhập điểm đón và điểm đến trước');
  const body={
    pickup:pickup.value,
    destination:destination.value,
    vehicle:vehicle.value,
    pickup_lat:pickup.dataset.lat||null,
    pickup_lon:pickup.dataset.lon||null,
    destination_lat:destination.dataset.lat||null,
    destination_lon:destination.dataset.lon||null
  };
  toast('Đang lấy bản đồ + tuyến đường thực...');
  let r=await fetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let j=await r.json();
  if(!j.ok)return toast(j.error||'Không tìm được tuyến thực');
  window.routeData=j; window.routes=j.routes;
  document.getElementById('routes').innerHTML=j.routes.map((x,i)=>{
    const f=x.fare||{};
    return `<div class="route ${i===0?'sel':''}" data-route-index="${i}">
      <h3>${i===0?'⚡ ':'🔀 '}${x.type}</h3>
      <p>📏 <b>${x.distance} km</b> · ⏱️ <b>${x.duration} phút</b></p>
      <p class="muted">Cơ bản ${Number(f.base||0).toLocaleString('vi-VN')}đ · vượt ${Number(f.extra_km||0).toFixed(2)} km</p>
      <b>${Number(x.price||0).toLocaleString('vi-VN')}đ</b>
    </div>`;
  }).join('');
  document.querySelectorAll('[data-route-index]').forEach(el=>el.addEventListener('click',()=>chooseRoute(Number(el.dataset.routeIndex))));
  loadWeather(j.pickup.lat,j.pickup.lon);
  go('route');
  setTimeout(()=>drawRealRoute(j),220);
}
function drawRealRoute(j){
  if(!map)initMap();
  clearRealLayers();
  const p=[j.pickup.lat,j.pickup.lon], q=[j.destination.lat,j.destination.lon];
  pickupMarker=L.marker(p).addTo(map).bindPopup('<b>📍 Điểm đón</b><br>'+escapeHtml(j.pickup.display_name));
  destinationMarker=L.marker(q).addTo(map).bindPopup('<b>🏁 Điểm đến</b><br>'+escapeHtml(j.destination.display_name));
  routeLayers=[];
  (j.routes||[]).forEach((r,i)=>{
    const coords=(r.geometry&&r.geometry.coordinates||[]).map(c=>[c[1],c[0]]);
    if(coords.length<2)return;
    const layer=L.polyline(coords,{color:i===0?'#00b14f':'#64748b',weight:i===0?7:4,opacity:i===0?.95:.55,dashArray:i===0?null:'8 8'}).addTo(map);
    routeLayers.push(layer);
  });
  if(routeLayers.length) map.fitBounds(routeLayers[0].getBounds(),{padding:[40,40]});
  else map.fitBounds(L.latLngBounds([p,q]),{padding:[40,40]});
  const r=j.routes[0]||{};
  const f=r.fare||{};
  document.getElementById('placeInfo').innerHTML=
    '<b>📍 Điểm đón:</b> '+escapeHtml(j.pickup.display_name)+
    '<br><b>🏁 Điểm đến:</b> '+escapeHtml(j.destination.display_name)+
    '<br><b>📏 Quãng đường thực:</b> '+r.distance+' km'+
    '<br><b>⏱️ Thời gian dự kiến:</b> '+r.duration+' phút'+
    '<br><b>💰 Giá chuyến:</b> '+Number(r.price||0).toLocaleString('vi-VN')+'đ'+
    '<br><span class="muted">Nguồn: OpenStreetMap + OSRM</span>';
  const steps=(r.steps||[]).map(s=>s.name).filter(Boolean);
  document.getElementById('routeSteps').classList.remove('hidden');
  document.getElementById('stepsList').innerHTML=steps.length
    ? [...new Set(steps)].slice(0,20).map(x=>`<div>📍 ${escapeHtml(x)}</div>`).join('')
    : '<span class="muted">OSRM không trả tên đường cho đoạn này.</span>';
}
function clearRealLayers(){if(!map)return;routeLayers.forEach(x=>map.removeLayer(x));routeLayers=[];if(pickupMarker){map.removeLayer(pickupMarker);pickupMarker=null}if(destinationMarker){map.removeLayer(destinationMarker);destinationMarker=null}}
async function loadWeather(lat,lon){try{let r=await fetch('/api/weather',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat,lon})});let j=await r.json();if(!j.ok)return;let c=j.current;document.getElementById('weatherTemp').textContent=Math.round(c.temperature_2m)+'°';document.getElementById('weatherHum').textContent=Math.round(c.relative_humidity_2m)+'%';document.getElementById('weatherRain').textContent=(c.rain||c.precipitation||0)+' mm';document.getElementById('weatherLabel').textContent=j.label+' · Gió '+Math.round(c.wind_speed_10m)+' km/h'}catch(e){}}
function chooseRoute(i){
  selectedRoute=window.routes[i];
  document.querySelectorAll('.route').forEach((x,k)=>x.classList.toggle('sel',k===i));
  const f=selectedRoute.fare||{};
  document.getElementById('payTotal').textContent=Number(selectedRoute.price||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billTotal').textContent=Number(selectedRoute.price||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billBase').textContent=Number(f.base||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billExtra').textContent=Number(f.extra_fee||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billDistance').textContent=selectedRoute.distance+' km';
  document.getElementById('billDuration').textContent=selectedRoute.duration+' phút';
  toast('Đã chọn '+selectedRoute.type+' · '+selectedRoute.distance+' km · '+Number(selectedRoute.price).toLocaleString('vi-VN')+'đ');
  setTimeout(()=>go('needs'),350);
}
function saveNeeds(){
  window.meetingInfo={
    shirt:shirtColor.value,
    bag:bagType.value,
    item:meetingItem.value.trim(),
    note:meetingNote.value.trim()
  };
  toast('Đã lưu nhu cầu + dấu hiệu nhận diện');
  setTimeout(()=>loadDrivers(),350);
}
async function loadDrivers(){
  let r=await fetch('/api/match',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({gender:gender.value,rating:minrating.value})});
  let j=await r.json();
  document.getElementById('drivers').innerHTML=j.drivers.map(d=>`<div class="card click" data-driver-id="${d.id}"><div class="driver"><div class="avatar">👤</div><div><b>${escapeHtml(d.name)}</b><div>⭐ ${d.rating} · ${d.trips} chuyến</div><div class="muted">${escapeHtml(d.vehicle)} · ${escapeHtml(d.plate)}</div></div></div></div>`).join('');
  document.querySelectorAll('[data-driver-id]').forEach(el=>el.addEventListener('click',()=>chooseDriver(Number(el.dataset.driverId))));
  window.drivers=j.drivers; go('match');
}
async function chooseDriver(id){
  selectedDriver=window.drivers.find(x=>x.id===id);
  let r=await fetch('/api/trip',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    user_id:user.id,pickup:pickup.value,destination:destination.value,
    distance:selectedRoute?.distance||0,duration:selectedRoute?.duration||0,
    route_type:selectedRoute?.type||'Nhanh nhất',driver_id:id,total:selectedRoute?.price||0,
    meeting_info:window.meetingInfo||{}
  })});
  let j=await r.json(); if(!j.ok)return toast('Không tạo được chuyến');
  tripId=j.trip_id;
  document.getElementById('liveRoute').textContent=pickup.value+' → '+destination.value;
  document.getElementById('liveDriver').textContent=selectedDriver.name+' · ⭐'+selectedDriver.rating;
  document.getElementById('liveVehicle').textContent=selectedDriver.vehicle+' · '+selectedDriver.plate;
  document.getElementById('liveMeet').textContent=
    `👕 Áo: ${window.meetingInfo?.shirt||'chưa chọn'} · 🎒 ${window.meetingInfo?.bag||'chưa chọn'} · 👀 ${window.meetingInfo?.item||'không có vật nhận diện'}${window.meetingInfo?.note?' · 📝 '+window.meetingInfo.note:''}`;
  const f=selectedRoute?.fare||{};
  document.getElementById('payTotal').textContent=Number(selectedRoute?.price||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billTotal').textContent=Number(selectedRoute?.price||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billBase').textContent=Number(f.base||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billExtra').textContent=Number(f.extra_fee||0).toLocaleString('vi-VN')+'đ';
  document.getElementById('billDistance').textContent=(selectedRoute?.distance||0)+' km';
  document.getElementById('billDuration').textContent=(selectedRoute?.duration||0)+' phút';
  go('live'); timerStart=Date.now(); startLiveMap(); tick();
}
function tick(){if(currentView==='live'&&timerStart){let s=Math.floor((Date.now()-timerStart)/1000);liveTime.textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');setTimeout(tick,1000)}}
function startLiveMap(){
  const route=selectedRoute?.geometry;
  if(!route||!route.coordinates?.length)return;
  const path=route.coordinates.map(c=>[c[1],c[0]]);
  if(path.length<2)return;
  liveStep=0;
  const icon=L.divIcon({className:'rovia-car-icon',html:'<div style="font-size:30px;filter:drop-shadow(0 2px 2px #555)">🏍️</div>',iconSize:[36,36],iconAnchor:[18,18]});
  if(!liveMap){
    liveMap=L.map('liveMap').setView(path[0],16);
    addMapTiles(liveMap);
    liveLine=L.polyline(path,{color:'#94a3b8',weight:6,opacity:.8}).addTo(liveMap);
    liveProgress=L.polyline([path[0]],{color:'#00b14f',weight:8,opacity:.95}).addTo(liveMap);
    liveMarker=L.marker(path[0],{icon}).addTo(liveMap).bindPopup('🏍️ Tài xế ROVIA');
  }else{
    liveLine.setLatLngs(path);
    liveProgress.setLatLngs([path[0]]);
    liveMarker.setLatLng(path[0]);
  }
  liveMap.fitBounds(liveLine.getBounds(),{padding:[35,35]});
  setTimeout(()=>liveMap.invalidateSize(true),220);
  clearInterval(liveTimer);
  liveTimer=setInterval(()=>{
    if(currentView!=='live'){clearInterval(liveTimer);return;}
    liveStep=Math.min(liveStep+1,path.length-1);
    const currentPath=path.slice(0,liveStep+1);
    liveMarker.setLatLng(path[liveStep]);
    liveProgress.setLatLngs(currentPath);
    liveMap.panTo(path[liveStep],{animate:true,duration:.35});
    const ratio=liveStep/(path.length-1);
    const total=selectedRoute?.distance||0;
    const remain=Math.max(0,(1-ratio)*total);
    const eta=Math.max(0,Math.ceil((1-ratio)*(selectedRoute?.duration||0)));
    document.getElementById('etaStatus').textContent='ETA: '+eta+' phút';
    document.getElementById('distanceStatus').textContent='Còn: '+remain.toFixed(2)+' km';
    document.getElementById('driverStatus').textContent=ratio<1?'🟢 Tài xế đang trên tuyến thực tế':'🏁 Tài xế đã tới điểm đến';
    if(liveStep>=path.length-1)clearInterval(liveTimer);
  },900);
}
function finishTrip(){clearInterval(liveTimer);liveTimer=null;document.getElementById('driverStatus').textContent='🏁 Chuyến đã kết thúc';toast('Chuyến đã kết thúc');setTimeout(()=>go('payment'),500)}
async function pay(method){await fetch('/api/pay',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({trip_id:tripId,method})});toast('Thanh toán thành công · '+method);setTimeout(()=>go('rating'),600)}
async function rateTrip(){await fetch('/api/rating',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({trip_id:tripId,rating:ratingVal.value,comment:comment.value})});toast('Đã gửi đánh giá');setTimeout(()=>go('rewards'),600)}
async function runFuzzy(){let r=await fetch('/api/fuzzy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({distance:fd.value,traffic:ft.value,demand:fm.value,weather:fw.value,rating:fr.value,punctuality:fp.value})});let j=await r.json();fuzzyResult.innerHTML='<b>Price:</b> '+j.price+'<br><b>Points:</b> '+j.points}
async function loadHistory(){let r=await fetch('/api/history');let j=await r.json();adminTrips.textContent=j.trips.length;toast('Đã cập nhật Admin')}
function addMapTiles(m){
  const layers=[
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}),
    L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',{subdomains:'abc',maxZoom:19,attribution:'© OpenStreetMap, HOT'}),
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:20,attribution:'© OpenStreetMap © CARTO'})
  ];
  let idx=0;
  const use=(layer)=>{
    m.eachLayer(l=>{if(l instanceof L.TileLayer)m.removeLayer(l)});
    layer.addTo(m);
    let failed=false;
    layer.on('tileerror',()=>{
      if(failed)return;
      failed=true;
      idx++;
      if(idx<layers.length)use(layers[idx]);
      else toast('Không tải được lớp bản đồ thật. Kiểm tra Internet rồi tải lại.');
    });
  };
  use(layers[0]);
}
function initMap(){if(map)return;map=L.map('map',{preferCanvas:true,zoomControl:true}).setView([10.2433,105.9722],13);addMapTiles(map);setTimeout(()=>map.invalidateSize(true),120)}
document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>go(b.dataset.v));
// Demo account screen first.
document.getElementById('auth').style.display='grid';
</script></body></html>'''

@APP.route('/')
def home(): return render_template_string(HTML)

# Google Colab launcher — ONE Flask server only.
import socket

def find_free_port(start=5000, end=5100):
    for port in range(start,end):
        s=socket.socket()
        try:
            s.bind(('127.0.0.1',port))
            s.close()
            return port
        except OSError:
            s.close()
    raise RuntimeError('Không tìm thấy port trống.')

ROVIA_PORT=find_free_port(5000,5100)

def start_rovia():
    def run(): APP.run(host='0.0.0.0',port=ROVIA_PORT,debug=False,use_reloader=False)
    threading.Thread(target=run,daemon=True).start(); time.sleep(1)
    print(f'🚗 ROVIA ONE APP — 1 APP / 1 SERVER / 1 DATABASE — PORT {ROVIA_PORT}')
    try:
        from google.colab import output
        output.serve_kernel_port_as_iframe(ROVIA_PORT,path='/',height=900)
    except Exception:
        print(f'Mở tại http://127.0.0.1:{ROVIA_PORT}')

start_rovia()
