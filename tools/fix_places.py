# -*- coding: utf-8 -*-
"""data/places-kansai.json 후처리(생성기 build_places.py 뒤에 실행).
- 체인 상점(돈키호테·다이소·유니클로 등)이 '명소'로 들어온 행 → '쇼핑'
- 한국어 표기의 ';' 대안 표기는 첫 표기만 남김, 전각 공백 정리
- 같은 이름이 300m 안에 겹치면 하나만(인기 높은 쪽, 같으면 교통>쇼핑>호텔>전망>명소>카페>식당>페리>동네)
사용: python -I -X utf8 tools/fix_places.py data/places-kansai.json
"""
import json, re, sys, math, gzip
SHOP2_RE = re.compile(r"ドン・?キホーテ|ドンキ|don quijote|donki|ダイソー|daiso|ユニクロ|uniqlo|ビックカメラ|bic ?camera|ヨドバシ|yodobashi|ロフト|\bloft\b|無印良品|muji|アニメイト|animate|まんだらけ|mandarake|ポケモンセンター|pok[eé]mon center|ニンテンドーオオサカ|ニンテンドー大阪|nintendo osaka|nintendo kyoto|キデイランド|kiddy ?land|サンリオ|sanrio|ディズニーストア|disney store|tsutaya|蔦屋|ABC-?MART|ＡＢＣマート|\bGU\b|ジーユー|マツモトキヨシ|matsumoto ?kiyoshi|スギ薬局|コスモス薬品|ココカラ|kokumin|コクミン|ウエルシア|welcia", re.I)
NOT_SHOP = re.compile(r"museum|ミュージアム|world|ワールド|studios|スタジオ|観覧車|ferris", re.I)
PREF = {"교통": 0, "쇼핑": 1, "호텔": 2, "전망": 3, "명소": 4, "카페": 5, "식당": 6, "페리": 7, "동네": 8}
path = sys.argv[1]
d = json.load(open(path, encoding="utf-8")); items = d["items"]
KO_FIX = {"黒門寿司": "구로몬 스시"}   # AI 표기 오류 수동 보정
n_shop = n_semi = 0
for x in items:
    if x[5] == "명소" and SHOP2_RE.search((x[1] or "") + " " + (x[2] or "")): x[5] = "쇼핑"; n_shop += 1
    if x[5] == "쇼핑" and NOT_SHOP.search((x[1] or "") + " " + (x[2] or "")): x[5] = "명소"; n_shop -= 1
    if x[2] in KO_FIX: x[0] = KO_FIX[x[2]]
    if x[0] and ";" in x[0]: x[0] = x[0].split(";")[0].strip(); n_semi += 1
    for i in (0, 1, 2, 7):
        if x[i] and "　" in x[i]: x[i] = re.sub(r"\s+", " ", x[i].replace("　", " ")).strip()
# dedup
groups = {}
for idx, x in enumerate(items):
    key = (x[2] or x[1] or x[0]).lower().strip()
    groups.setdefault(key, []).append(idx)
drop = set()
for key, idxs in groups.items():
    if len(idxs) < 2: continue
    keep = []
    for i in sorted(idxs, key=lambda i: (-items[i][6], PREF.get(items[i][5], 9))):
        xi = items[i]
        dup = False
        for k in keep:
            xk = items[k]
            dist = math.hypot((xi[3] - xk[3]) * 111000, (xi[4] - xk[4]) * 91000)
            if dist <= 300: dup = True; break
        if dup:
            drop.add(i)
            # 겹치는 쪽 이름이 비어 있으면 남는 쪽에 채워 준다
            for j in (0, 1, 2):
                if not items[k][j] and xi[j]: items[k][j] = xi[j]
        else: keep.append(i)
items = [x for i, x in enumerate(items) if i not in drop]
d["items"] = items
data = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
open(path, "wb").write(data)
print("shop fixed", n_shop, "semicolon fixed", n_semi, "dedup dropped", len(drop), "items", len(items), "raw", len(data), "gz", len(gzip.compress(data, 9)))
