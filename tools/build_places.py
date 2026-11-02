# -*- coding: utf-8 -*-
"""Osaka/Kyoto/Nara/Kobe/KIX place dictionary generator (adapted from tools/build_places.py).
Run: python -I build_places_kansai.py --fetch | --ko | --build   (raw cache: places_raw_kansai/)
Format v2: [ko,en,ja,lat,lng,kind,pop,cuisine,kosrc]
"""
import io, json, os, re, sys, time, gzip, collections, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "places_raw_kansai")
OUT = os.path.join(ROOT, "places-kansai.json")
UA = "tokki-trip/0.2 (github minsukwkd-hub/moneyeo-hongkong; place index builder, kansai)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://lz4.overpass-api.de/api/interpreter"]

ALLCATS = ["tourism", "historic", "restaurant", "cafe", "fastfood", "shop", "market", "park", "nature",
           "station", "ferry", "aerial", "place", "temple", "bakery", "gift"]
CORECATS = ALLCATS + ["shop2"]
WIDECATS = ["tourism", "historic", "park", "nature", "station", "aerial", "ferry", "shop", "market", "temple", "place", "gift", "bakery"]
REGIONS = {  # south,west,north,east (cores first, then wide)
    "osaka": ("34.60,135.40,34.76,135.58", CORECATS),
    "kyoto": ("34.93,135.68,35.08,135.82", CORECATS),
    "nara": ("34.66,135.80,34.70,135.85", CORECATS),
    "kobe": ("34.66,135.16,34.72,135.22", CORECATS),
    "kix": ("34.42,135.22,34.44,135.25", ["tourism", "station", "shop", "cafe", "restaurant"]),
    "osaka_wide": ("34.50,135.30,34.90,135.70", WIDECATS),
    "kyoto_wide": ("34.85,135.60,35.12,135.88", WIDECATS),
    "nara_wide": ("34.55,135.70,34.75,135.90", WIDECATS),
    "kobe_wide": ("34.62,135.05,34.82,135.35", WIDECATS),
    "rinku": ("34.39,135.27,34.43,135.33", ["shop", "tourism", "station"]),
}
WIDE_CORE = {"osaka_wide": "osaka", "kyoto_wide": "kyoto", "nara_wide": "nara", "kobe_wide": "kobe"}
SHOP2_RE = re.compile(r"ドン・?キホーテ|ドンキ|don quijote|donki|ダイソー|daiso|ユニクロ|uniqlo|ビックカメラ|bic ?camera|ヨドバシ|yodobashi|ロフト|loft|無印良品|muji|アニメイト|animate|まんだらけ|mandarake|ポケモン|pok[eé]mon|ニンテンドー|nintendo|キデイランド|kiddy ?land|サンリオ|sanrio|ディズニーストア|disney store|tsutaya|蔦屋|ABC-?MART|ＡＢＣ|GU|ジーユー|マツモトキヨシ|matsumoto ?kiyoshi|スギ薬局|sugi|コスモス|cosmos|ココカラ|kokumin|コクミン|ウエルシア|welcia", re.I)
CATS = {  # each value = list of selectors (bbox is appended to each)
    "tourism": ['nwr["tourism"~"^(attraction|museum|viewpoint|artwork|gallery|zoo|theme_park|aquarium|hotel|resort)$"]["name"]'],
    "historic": ['nwr["historic"]["name"]'],
    "restaurant": ['nwr["amenity"="restaurant"]["name"]'],
    "cafe": ['nwr["amenity"~"^(cafe|ice_cream|food_court|bar|pub)$"]["name"]'],
    "fastfood": ['nwr["amenity"="fast_food"]["name"]'],
    "shop": ['nwr["shop"~"^(mall|department_store)$"]["name"]'],
    "market": ['nwr["amenity"="marketplace"]["name"]'],
    "park": ['nwr["leisure"~"^(park|garden|nature_reserve|beach_resort)$"]["name"]'],
    "nature": ['nwr["natural"~"^(beach|peak)$"]["name"]'],
    "station": ['nwr["railway"="station"]["name"]', 'nwr["public_transport"="station"]["name"]'],
    "ferry": ['nwr["amenity"="ferry_terminal"]["name"]'],
    "aerial": ['nwr["aerialway"="station"]["name"]'],
    "place": ['nwr["place"~"^(suburb|neighbourhood|quarter|town|village)$"]["name"]'],
    "temple": ['nwr["amenity"="place_of_worship"]["name"]'],
    "bakery": ['nwr["shop"~"^(bakery|confectionery|pastry|tea|coffee|chocolate|ice_cream)$"]["name"]'],
    "gift": ['nwr["shop"~"^(gift|souvenir|books|cosmetics)$"]["name"]'],
    "shop2": ['nwr["shop"~"^(supermarket|variety_store|electronics|clothes|toys|anime|books|chemist|department_store)$"]["name"]'],
}

def http(url, data=None, headers=None, timeout=180):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")

def overpass_once(sels, bbox, off=0):
    q = "(" + "".join("%s(%s);" % (s, bbox) for s in sels) + ");"
    body = urllib.parse.urlencode({"data": "[out:json][timeout:110];%s out center tags qt;" % q}).encode()
    last = None
    for attempt in range(6):
        url = OVERPASS[(attempt + off) % len(OVERPASS)]
        try:
            return json.loads(http(url, body, {"Content-Type": "application/x-www-form-urlencoded"}, timeout=120))
        except Exception as e:
            last = e; wait = 10 * (attempt + 1)
            print("  retry", attempt + 1, url.split('/')[2], str(e)[:80], "wait", wait, flush=True); time.sleep(wait)
    raise last

def overpass(sels, bbox, off=0):
    try:
        return overpass_once(sels, bbox, off)
    except Exception as e:
        print("  whole bbox failed -> splitting into 4", str(e)[:60], flush=True)
        s, w, n, ee = [float(x) for x in bbox.split(",")]
        ms, mw = (s + n) / 2, (w + ee) / 2
        els = {}
        for b in ((s, w, ms, mw), (s, mw, ms, ee), (ms, w, n, mw), (ms, mw, n, ee)):
            d = overpass_once(sels, "%.4f,%.4f,%.4f,%.4f" % b, off)
            for el in d.get("elements", []): els[(el["type"], el["id"])] = el
            time.sleep(5)
        return {"elements": list(els.values())}

def fetch():
    os.makedirs(RAW, exist_ok=True)
    import threading, itertools
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(reg, k, bbox) for reg, (bbox, cats) in REGIONS.items() for k in cats
            if not os.path.exists(os.path.join(RAW, "%s_%s.json" % (reg, k)))]
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
        jobs = [j for j in jobs if j[0] in only]
    print("jobs", len(jobs), flush=True)
    failed = []; lock = threading.Lock(); cnt = itertools.count()
    def run(job):
        reg, k, bbox = job; off = next(cnt) % len(OVERPASS)
        fp = os.path.join(RAW, "%s_%s.json" % (reg, k)); t = time.time()
        try:
            d = overpass(CATS[k], bbox, off)
        except Exception as e:
            print("  FAILED", reg, k, str(e)[:100], flush=True)
            with lock: failed.append((reg, k))
            return
        if d.get("remark") and not d.get("elements"):
            print("  EMPTY-WITH-REMARK (not cached)", reg, k, d["remark"][:80], flush=True)
            with lock: failed.append((reg, k))
            return
        io.open(fp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        print("  done", reg, k, len(d.get("elements", [])), "elements", round(time.time() - t, 1), "s", flush=True)
        time.sleep(3)
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(run, jobs))
    print("FAILED categories:", failed, flush=True)
    if "--only" not in sys.argv: sparql_fetch()

SPARQL_BBOX = (134.85, 34.15, 136.10, 35.25)  # W,S,E,N
SPARQL_GROUPS = {
    "A_religion_nature": {"Q845945": "명소", "Q5393308": "명소", "Q23413": "명소", "Q92026": "명소", "Q22698": "명소", "Q1107656": "명소", "Q12280": "명소", "Q40080": "명소", "Q9259": "명소", "Q655311": "명소", "Q177380": "명소"},
    "B_attraction": {"Q570116": "명소", "Q33506": "명소", "Q11303": "명소", "Q177305": "전망", "Q1440300": "전망", "Q12518": "명소", "Q2416723": "명소", "Q194195": "명소", "Q2281788": "명소", "Q43501": "명소"},
    "C_transit_shop": {"Q55488": "교통", "Q330284": "쇼핑", "Q31374404": "쇼핑", "Q11315": "쇼핑", "Q216107": "쇼핑"},
}

def sparql_query(clss, box):
    w, s_, e, n = box
    return ("SELECT ?item ?lat ?lon ?sl ?ko ?en ?ja ?cls WHERE { VALUES ?cls { %s } "
            "SERVICE wikibase:box { ?item wdt:P625 ?loc . bd:serviceParam wikibase:cornerSouthWest \"Point(%s %s)\"^^geo:wktLiteral . "
            "bd:serviceParam wikibase:cornerNorthEast \"Point(%s %s)\"^^geo:wktLiteral } "
            "?item wdt:P31/wdt:P279* ?cls . ?item wikibase:sitelinks ?sl . FILTER(?sl >= 2) "
            "OPTIONAL { ?item rdfs:label ?ko . FILTER(lang(?ko) = \"ko\") } OPTIONAL { ?item rdfs:label ?en . FILTER(lang(?en) = \"en\") } "
            "OPTIONAL { ?item rdfs:label ?ja . FILTER(lang(?ja) = \"ja\") } "
            "BIND(geof:latitude(?loc) AS ?lat) BIND(geof:longitude(?loc) AS ?lon) }") % (" ".join("wd:" + c for c in clss), w, s_, e, n)

def sparql_run(clss, box, depth=0):
    q = sparql_query(clss, box)
    body = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    last = None
    for attempt in range(3):
        try:
            txt = http("https://query.wikidata.org/sparql", body, {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/sparql-results+json"}, timeout=120)
            return json.loads(txt)["results"]["bindings"]
        except Exception as e:
            last = e; print("  sparql retry", attempt, str(e)[:80], flush=True); time.sleep(65)
    if depth >= 2: raise last
    w, s_, e_, n = box; mw, ms = (w + e_) / 2, (s_ + n) / 2; out = []
    print("  sparql splitting bbox", flush=True)
    for b in ((w, s_, mw, ms), (mw, s_, e_, ms), (w, ms, mw, n), (mw, ms, e_, n)):
        time.sleep(65); out += sparql_run(clss, b, depth + 1)
    return out

def sparql_fetch():
    fp = os.path.join(RAW, "wd_sparql.json")
    cache = json.load(io.open(fp, encoding="utf-8")) if os.path.exists(fp) else {}
    for g, clss in SPARQL_GROUPS.items():
        if g in cache: print("sparql", g, "cached", len(cache[g])); continue
        print("sparql", g, flush=True)
        try:
            rows = sparql_run(list(clss), SPARQL_BBOX)
        except Exception as e:
            print("  SPARQL FAILED", g, str(e)[:100], flush=True); continue
        cache[g] = [{k: v.get("value", "") for k, v in r.items()} for r in rows]
        io.open(fp, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False))
        print("  rows", len(rows), flush=True); time.sleep(65)

def sparql_items():
    fp = os.path.join(RAW, "wd_sparql.json")
    if not os.path.exists(fp): return []
    cache = json.load(io.open(fp, encoding="utf-8")); best = {}
    for g, rows in cache.items():
        for r in rows:
            q = r["item"].rsplit("/", 1)[-1]; kind = SPARQL_GROUPS[g].get(r.get("cls", "").rsplit("/", 1)[-1], "명소")
            o = best.get(q)
            if not o: best[q] = o = {"q": q, "lat": float(r["lat"]), "lon": float(r["lon"]), "sl": int(r["sl"]), "ko": r.get("ko", ""), "en": r.get("en", ""), "ja": r.get("ja", ""), "kind": kind}
            elif KIND_PRI.get(kind, 0) > KIND_PRI.get(o["kind"], 0) and o["kind"] != "교통": o["kind"] = kind
    return list(best.values())

def wikidata_labels(qids):
    fp = os.path.join(RAW, "wd_labels.json")
    cache = json.load(io.open(fp, encoding="utf-8")) if os.path.exists(fp) else {}
    todo = [q for q in qids if q not in cache]
    print("wikidata labels: cached", len(cache), "todo", len(todo), flush=True)
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        params = {"action": "wbgetentities", "ids": "|".join(chunk), "props": "labels|sitelinks", "languages": "ko|en|ja", "format": "json"}
        for attempt in range(5):
            try:
                txt = http("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params), None, {"Accept": "application/json"}); break
            except Exception as e:
                print("  wd retry", attempt, str(e)[:80], flush=True); time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError("wikidata failed")
        ents = json.loads(txt).get("entities", {})
        for q in chunk:
            e = ents.get(q) or {}; lb = e.get("labels") or {}
            cache[q] = {"ko": (lb.get("ko") or {}).get("value", ""), "en": (lb.get("en") or {}).get("value", ""),
                        "ja": (lb.get("ja") or {}).get("value", ""), "sl": len(e.get("sitelinks") or {})}
        io.open(fp, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False))
        print("  ", i + len(chunk), "/", len(todo), flush=True); time.sleep(0.4)
    return cache

ASCII = re.compile(r"^[\x20-\x7e]+$")
JP = re.compile("[぀-ヿ㐀-鿿ｦ-ﾟ]")   # kana, CJK, half-width kana
HANGUL = re.compile(r"[가-힣]")

# ferry bias dropped: below station/attraction/hotel (Tempozan/USJ shuttle still keeps its kind)
KIND_PRI = {"교통": 8, "명소": 7, "호텔": 6, "전망": 5, "쇼핑": 4, "카페": 3, "식당": 2, "페리": 1.5, "동네": 1}

def kind_of(cat, t):
    tour = t.get("tourism", ""); am = t.get("amenity", "")
    if cat in ("station", "aerial") or t.get("railway") == "station" or t.get("public_transport") == "station": return "교통"
    if cat == "ferry" or am == "ferry_terminal": return "페리"
    if tour in ("attraction", "museum", "gallery", "zoo", "theme_park", "aquarium", "artwork") or cat in ("historic", "temple", "park"): return "명소"
    if tour in ("hotel", "resort"): return "호텔"
    if tour == "viewpoint" or "peak" in t.get("natural", ""): return "전망"
    if cat == "bakery": return "카페"
    if cat in ("shop", "shop2", "market", "gift"): return "쇼핑"
    if am in ("cafe", "ice_cream"): return "카페"
    if am in ("restaurant", "fast_food", "food_court", "bar", "pub"): return "식당"
    if cat == "place": return "동네"
    return "명소"

AI_SYS = ("너는 일본 오사카·교토·나라·고베(간사이) 장소 이름을 한국 여행자가 쓰는 한국어 표기로 바꾸는 변환기야. 입력은 [{\"i\":번호,\"en\":영문/로마자,\"ja\":일본어}] 배열이고, "
          "출력은 같은 번호의 [{\"i\":번호,\"ko\":한국어 표기}] JSON 배열만(설명·코드블록 없이). 규칙: 한국 여행자가 흔히 쓰는 표기가 있으면 그것을 쓴다"
          "(道頓堀→도톤보리, 黒門市場→구로몬 시장, 通天閣→츠텐카쿠, 清水寺→기요미즈데라, 大阪城→오사카성, 伏見稲荷大社→후시미이나리 신사, 奈良公園→나라 공원). "
          "한국에 이미 굳은 외래 지명·브랜드는 그대로(Starbucks→스타벅스, Universal Studios Japan→유니버설 스튜디오 재팬, Osaka Station→오사카역). "
          "없으면 일본어 발음(일본어 표기가 있으면 그쪽 기준, 없으면 로마자)을 외래어 표기법에 가깝게 자연스러운 한글로 옮기고, "
          "公園/神社/寺/駅/市場/橋/通/商店街/美術館/博物館 같은 일반 명사는 공원/신사/절(또는 -지·-데라 관용형)/역/시장/다리/거리/상점가/미술관/박물관으로 붙여 쓴다. 한자 음독(한국식 한자음)은 쓰지 마. 30자 이내.")

def _ai_call(model, sys_prompt, msg, timeout):
    url = "https://suzi-proxy.suzi-proxy.workers.dev/"
    body = {"model": model, "max_tokens": 4000, "stream": False, "system": sys_prompt, "messages": [{"role": "user", "content": msg}], "output_config": {"effort": "low"}}
    for attempt in range(5):
        try:
            return http(url, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json", "Origin": "http://localhost:8765", "anthropic-version": "2023-06-01"}, timeout=timeout)
        except Exception as e:
            print("  ai retry", attempt, str(e)[:100], flush=True); time.sleep(10 * (attempt + 1))
    return None

def ai_korean_names(cands):
    """[(key,en,ja)] -> {key: ko}; cached in places_raw_kansai/ko_ai.json"""
    fp = os.path.join(RAW, "ko_ai.json")
    cache = json.load(io.open(fp, encoding="utf-8")) if os.path.exists(fp) else {}
    todo = [c for c in cands if c[0] not in cache]
    print("ai korean names: cached", len(cache), "todo", len(todo), flush=True)
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock(); done = [0]
    def run_chunk(chunk):
        msg = json.dumps([{"i": k, "en": c[1], "ja": c[2]} for k, c in enumerate(chunk)], ensure_ascii=False)
        txt = _ai_call("claude-haiku-5-5", AI_SYS, msg, 120)
        arr = []
        if txt:
            try:
                r = json.loads(txt); text = "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
                m = re.search(r"\[[\s\S]*\]", text); arr = json.loads(m.group(0)) if m else []
            except Exception as e:
                print("  parse fail", str(e)[:80], flush=True)
        got = 0
        with lock:
            for o in arr:
                try:
                    k = int(o.get("i")); ko = str(o.get("ko", "")).strip()[:30]
                    if 0 <= k < len(chunk) and ko and HANGUL.search(ko): cache[chunk[k][0]] = ko; got += 1
                except Exception: pass
            if txt:
                for c in chunk: cache.setdefault(c[0], "")
            io.open(fp, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False))
            done[0] += len(chunk); print("  ", done[0], "/", len(todo), "got", got, flush=True)
        time.sleep(1.0)
    chunks = [todo[i:i + 40] for i in range(0, len(todo), 40)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(run_chunk, chunks))
    return cache

def pick_names(t, wd):
    ko = t.get("name:ko") or (wd.get("ko") if wd else "") or ""
    name = t.get("name", "")
    en = t.get("name:en") or (wd.get("en") if wd else "") or ""
    ja = t.get("name:ja") or ""
    if not ja and JP.search(name): ja = name
    if not ja and wd and wd.get("ja"): ja = wd["ja"]
    if not en and ASCII.match(name): en = name
    if not en: en = t.get("name:ja-Latn") or t.get("name:ja_rm") or ""
    if name and not ASCII.match(name) and JP.search(name) and not en:   # "Osaka Castle" mixed names
        m = re.match(r"^([^\x20-\x7e]+)\s+([\x20-\x7e]+)$", name)
        if m: ja = ja or m.group(1); en = m.group(2)
    if not en: en = ja   # fallback: Japanese name
    return ko.strip(), en.strip(), ja.strip()

CHOME = re.compile(r"丁目|초메$")
CHAIN = re.compile("一蘭|金龍|千房|だるま|はなまる|丸亀|スシロー|くら寿司|松屋|吉野家|すき家|CoCo壱|天下一品|一風堂|鳥貴族|焼肉|りくろー|PABLO|551|蓬莱|自由軒|北極星|道頓堀今井|美々卯|本家", re.I)
JUNKNAME = re.compile(r"^[\W\d_]+$")
EXCL = re.compile(r"playground|football pitch|basketball|sports ground|児童遊園|ちびっこ広場|遊び場|運動場|グラウンド|界石", re.I)

def load_raw():
    raw = []; qids = set()
    only = sys.argv[sys.argv.index("--regions") + 1].split(",") if "--regions" in sys.argv else None
    for reg, (bbox, cats) in REGIONS.items():
        if only and reg not in only: continue
        for k in cats:
            fp = os.path.join(RAW, "%s_%s.json" % (reg, k))
            if not os.path.exists(fp): print("missing", reg, k); continue
            els = json.load(io.open(fp, encoding="utf-8")).get("elements", [])
            raw.append((reg, k, els))
            for e in els:
                q = (e.get("tags") or {}).get("wikidata", "")
                if re.match(r"^Q\d+$", q): qids.add(q)
    return raw, qids

def build():
    raw, qids = load_raw()
    wd = wikidata_labels(sorted(qids))
    items = {}   # key -> [ko,en,ja,lat,lng,kind,pop,cuisine,kosrc, hasWD, region, cat]
    for reg, cat, els in raw:
        for e in els:
            t = e.get("tags") or {}
            lat = e.get("lat") or (e.get("center") or {}).get("lat"); lon = e.get("lon") or (e.get("center") or {}).get("lon")
            if lat is None or lon is None: continue
            lat = float(lat); lon = float(lon)
            if EXCL.search(" ".join([t.get("name", ""), t.get("name:en", "")])): continue
            if cat == "shop2" and not SHOP2_RE.search(" ".join([t.get("name", ""), t.get("name:en", ""), t.get("name:ja", ""), t.get("brand", ""), t.get("brand:en", "")])): continue
            if reg in WIDE_CORE:   # skip what the core bbox already covers
                cs, cw, cn, ce = [float(v) for v in REGIONS[WIDE_CORE[reg]][0].split(",")]
                if cs <= lat <= cn and cw <= lon <= ce: continue
            q = t.get("wikidata", ""); w = wd.get(q) if q else None
            ko, en, ja = pick_names(t, w)
            if not (ko or en or ja): continue
            if HANGUL.search(t.get("name", "")) and not ko: ko = t.get("name")
            kind = kind_of(cat, t)
            if cat == "place" or t.get("place"):
                if CHOME.search(" ".join([t.get("name", ""), t.get("name:ja", ""), ko, ja])): continue
                if t.get("place") == "neighbourhood" and not q and not t.get("name:en") and not ko: continue
            if len(ja) > 30 or len(en) > 30 or "　" in (ja + en + t.get("name", "")): continue
            if JUNKNAME.match(ja or en or ko): continue
            if t.get("historic") in ("memorial", "monument", "stone", "wayside_cross") and not q and not ko: continue
            pop = 0
            if w: pop += 1 + min(2, (w.get("sl") or 0) // 5)
            if ko: pop += 1
            if t.get("tourism") in ("attraction", "museum", "viewpoint", "theme_park", "zoo", "aquarium"): pop += 1
            if cat == "fastfood": pop -= 1
            cuisine = t.get("cuisine", "").replace("_", " ").replace(";", ", ")[:40]
            key = ("wd:" + q) if q else ((ja or en or ko).lower() + "|" + str(round(lat, 3)) + "," + str(round(lon, 3)))
            it = [ko, en, ja, round(lat, 5), round(lon, 5), kind, pop, cuisine, "", bool(w), reg, cat, bool(t.get("name:en"))]
            if key in items:
                old = items[key]
                for i in (0, 1, 2, 7):
                    if not old[i] and it[i]: old[i] = it[i]
                old[6] = max(old[6], pop); old[9] = old[9] or it[9]; old[12] = old[12] or it[12]
                if KIND_PRI.get(kind, 0) > KIND_PRI.get(old[5], 0): old[5] = kind
            else:
                items[key] = it
    if "--regions" not in sys.argv:   # Wikidata SPARQL pass: famous places outrank sub-features
        added = merged = 0
        for r in sparql_items():
            ko, en, ja = r["ko"], r["en"] or r["ja"], r["ja"]
            if len(ja) > 30 or len(en) > 30 or "　" in (ja + en): continue
            if not (ko or en or ja): continue
            key = "wd:" + r["q"]
            alt = (ja or en or ko).lower() + "|" + str(round(r["lat"], 3)) + "," + str(round(r["lon"], 3))
            old = items.get(key) or items.get(alt)
            if old:
                for i, v in ((0, ko), (1, en), (2, ja)):
                    if not old[i] and v: old[i] = v
                old[6] = max(old[6], r["sl"]); old[9] = True; merged += 1
                if KIND_PRI.get(r["kind"], 0) > KIND_PRI.get(old[5], 0): old[5] = r["kind"]
            else:
                items[key] = [ko, en, ja, round(r["lat"], 5), round(r["lon"], 5), r["kind"], r["sl"] + (1 if ko else 0), "", "", True, "wd", "sparql", False]; added += 1
        print("sparql merged", merged, "added", added, flush=True)
    out = [x for x in items.values() if x[5] == "교통" or not CHOME.search(x[2] + " " + x[0])]   # chome blocks out (station names stay)
    print("after chome filter", len(out), flush=True)

    def known(x): return x[9] or x[12] or x[7] or x[6] > 0 or CHAIN.search((x[2] or "") + " " + (x[1] or ""))

    def cand_list(tier):
        cands = []
        for x in out:
            if x[0] or not (x[1] or x[2]): continue
            if x[5] in ("식당", "카페") and not known(x): continue
            if x[5] in ("동네", "전망") and x[6] < 1 and not x[1]: continue
            if tier >= 1 and x[5] in ("식당", "카페") and not (x[9] or x[6] > 0 or CHAIN.search((x[2] or "") + " " + (x[1] or ""))): continue
            if tier >= 2 and x[11] in ("temple", "park", "historic") and not x[9] and x[6] < 2: continue
            if tier >= 3 and x[5] in ("식당", "카페", "쇼핑") and x[6] < 2: continue
            cands.append(((x[1] or "") + "|" + (x[2] or ""), x[1], x[2]))
        seen = {}; uniq = []
        for c in cands:
            if c[0] not in seen: seen[c[0]] = 1; uniq.append(c)
        return uniq

    ai = {}
    fp = os.path.join(RAW, "ko_ai.json")
    if os.path.exists(fp): ai = json.load(io.open(fp, encoding="utf-8"))
    if "--ko" in sys.argv:
        tier = 0
        while True:
            uniq = cand_list(tier)
            todo = [c for c in uniq if c[0] not in ai]
            print("ESTIMATE tier %d: %d unique candidates, %d to generate (~%d batches)" % (tier, len(uniq), len(todo), (len(todo) + 39) // 40), flush=True)
            if len(uniq) <= 35000 or tier >= 3: break
            print("  > 35000, tightening filter", flush=True); tier += 1
        if len(uniq) > 35000:
            print("STILL > 35000 after tightening; aborting"); sys.exit(2)
        ai = ai_korean_names(uniq)
    n = 0
    for x in out:
        if not x[0]:
            ko = ai.get((x[1] or "") + "|" + (x[2] or ""), "")
            if ko: x[0] = ko; x[8] = "ai"; n += 1
    print("ai ko applied", n)
    order = {"명소": 0, "전망": 1, "쇼핑": 2, "호텔": 3, "교통": 4, "식당": 5, "카페": 6, "페리": 7, "동네": 8}
    out.sort(key=lambda x: (-x[6], order.get(x[5], 9), x[0] or x[1] or x[2]))
    def encode(o):
        d = {"v": 2, "src": "OpenStreetMap(ODbL) + Wikidata(CC0) + 한국어 표기 일부 AI 추정(kosrc=ai), %s, 오사카·교토·나라·고베" % time.strftime("%Y-%m-%d"),
             "fields": ["ko", "en", "ja", "lat", "lng", "kind", "pop", "cuisine", "kosrc"], "items": [x[:9] for x in o]}
        return json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    data = encode(out)
    for lvl in (1, 2, 3):
        if len(gzip.compress(data, 9)) <= 1300000: break
        before = len(out)
        if lvl == 1: out = [x for x in out if not (x[5] == "식당" and not (x[9] or x[12] or x[7] or x[6] > 0))]
        elif lvl == 2: out = [x for x in out if not (x[5] in ("식당", "카페") and not (x[9] or x[6] > 0))]
        else: out = [x for x in out if not (x[5] in ("식당", "카페") and not x[9])]
        print("size ceiling: level", lvl, "dropped", before - len(out), flush=True)
        data = encode(out)
    rows = [x[:9] for x in out]
    doc = {"v": 2, "src": "OpenStreetMap(ODbL) + Wikidata(CC0) + 한국어 표기 일부 AI 추정(kosrc=ai), %s, 오사카·교토·나라·고베" % time.strftime("%Y-%m-%d"),
           "fields": ["ko", "en", "ja", "lat", "lng", "kind", "pop", "cuisine", "kosrc"], "items": rows}
    io.open(OUT, "wb").write(data)
    report(out, data)

def report(out, data):
    kinds = collections.Counter(x[5] for x in out); regs = collections.Counter(x[10] for x in out)
    kos = sum(1 for x in out if x[0]); ai = sum(1 for x in out if x[8] == "ai")
    gz = len(gzip.compress(data, 9))
    L = ["# Kansai place dictionary report (%s)" % (sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "final"), "", "Total items: %d" % len(out),
         "Korean name: %d (%.1f%%), of which AI-estimated: %d, from OSM/Wikidata: %d" % (kos, 100.0 * kos / max(1, len(out)), ai, kos - ai),
         "Size: raw %d bytes (%.2f MB), gzip %d bytes (%.0f KB)" % (len(data), len(data) / 1048576, gz, gz / 1024), "",
         "## Per kind"] + ["- %s: %d" % (k, v) for k, v in kinds.most_common()] + ["", "## Per region (first region seen)"] + ["- %s: %d" % (k, v) for k, v in regs.most_common()]
    core = sum(v for k, v in regs.items() if k in ("osaka", "kyoto", "nara", "kobe", "kix")); wide = sum(v for k, v in regs.items() if k not in ("osaka", "kyoto", "nara", "kobe", "kix"))
    L += ["", "## Core vs wide", "- core (osaka/kyoto/nara/kobe/kix): %d" % core, "- wide (*_wide + rinku + wd sparql-only): %d" % wide]
    L += ["", "## Korean coverage per kind"] + ["- %s: %d/%d" % (k, sum(1 for x in out if x[5] == k and x[0]), v) for k, v in kinds.most_common()]
    L += ["", "## Sample rows (ko | en | ja | lat,lng | kind | pop | kosrc)"]
    qs = [("도톤보리", "dotonbori|道頓堀"), ("구로몬", "kuromon|黒門"), ("유니버설", "universal|ユニバーサル"), ("가이유칸", "kaiyukan|海遊館"),
          ("오사카성", "osaka castle|大阪城"), ("후시미이나리", "fushimi inari|伏見稲荷"), ("나라공원", "nara park|奈良公園"), ("난바역", "namba|なんば|難波")]
    for kq, pat in qs:
        r = re.compile(kq + "|" + pat, re.I)
        hits = [x for x in out if r.search(" ".join([x[0], x[1], x[2]]))][:3]
        L.append("")
        L.append("### %s -> %d shown" % (kq, len(hits)))
        for x in hits:
            L.append("- %s | %s | %s | %s,%s | %s | %s | %s" % (x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[8] or "-"))
    io.open(os.path.join(ROOT, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("items", len(out), "with ko", kos, "ai", ai, "bytes", len(data), "gzip", gz, dict(kinds), dict(regs))

if __name__ == "__main__":
    args = sys.argv[1:] or ["--fetch", "--build"]
    if "--fetch" in args: fetch()
    if "--sparql" in args: sparql_fetch()
    if "--build" in args or "--ko" in args: build()
