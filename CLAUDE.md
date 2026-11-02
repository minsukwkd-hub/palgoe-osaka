# 팔괴 여정 (travel-maker VER 2 · 오사카)

휴대폰 우선 여행 일정 페이지. "토끼의 여정" VER 1(홍콩 편, 저장소 `minsukwkd-hub/moneyeo-hongkong`, 태그 `v1-hongkong`)을 2026-11-02에 복제해 만든 **VER 2**. 사용자 일행은 어른 5·아이 2, 총 7명("팔괴"). 서비스 이름은 **"팔괴 여정"** (제목·앱명·공유 미리보기). 도우미는 여전히 "토끼", 물어보기 버튼 기본 호칭은 **"시우·재이"**(`askName()`).

## 확정된 여행 정보 (2026-11-02 사용자 제공)
- 여행지 오사카(KIX) · 2026-12-18(금) ~ 12-21(월) 3박 4일
- 항공편 이스타항공 ZE615 ICN 09:55 → KIX 11:55 (T1) / ZE614 KIX 18:00 → ICN 19:50 (T1). 12월 시각은 예약 확인서가 최종.
- 숙소 칸데오 호텔 오사카 난바 (東心斎橋 2-2-5, 34.6707/135.5057, 체크인 15:00·아웃 11:00, 최상층 스카이스파)
- 기록 방식: 각자 기기에 기록(VER 1과 같음). 여러 명이 한 여정에 함께 기록하는 동기화(M5)는 미정.

## VER 1과 다른 점 (코드)
- **저장 키 전부 `palgoe-` 접두사** (`palgoe-trips-v1`, `palgoe-trip:<id>`, `palgoe-settings-v1`, `palgoe-chat-v1`, `palgoe-places-v1`, `palgoe-info-v1`, `palgoe-conn-v1`, `palgoe-variant`), IndexedDB `palgoe`. 이유: 두 저장소가 같은 `minsukwkd-hub.github.io` origin이라 localStorage를 공유한다. 내보내기 파일의 `kind:"tokki-trip"`은 호환을 위해 그대로.
- 지역: `AREAS` 9개(난바·도톤보리 / 우메다·키타 / 오사카성 / 텐노지·신세카이 / 베이에어리어·USJ / 교토 / 나라 / 고베 / 간사이공항), `areaOf`는 시내 5개 중심점과의 최근접 + 교토(lat>34.85)·나라(lng>135.75)·고베(lng<135.30)·공항(lat<34.50). `regionOf`(오사카/교토/나라/고베/간사이공항)·`farOf`(당일치기 지역)·`farDay(d)`가 옛 `isMacauPt`/`d.macau` 역할. `inHK`는 이름만 남고 범위는 간사이(34.1~35.3, 134.8~136.2).
- 이동시간: 지역이 다르면 `TRAIN_MIN` 표(오사카↔교토 60·나라 50·고베 40·공항 55분 등)로 "전철 약 N분". 페리 모드 없음.
- 통화 `CURS=["JPY","KRW"]`, 기본 JPY. 숙소 지역 `LODGE_AREAS` 7개(난바·신사이바시·우메다·혼마치·텐노지·교토·고베), 기본 난바. 동행 기본값 "가족", `trip.party.note`("어른 5 · 아이 2") 보존.
- 지도: `LANDGEO.kansai`(OSM 해안선, 11개 폴리곤, 89KB, `asia`는 VER 1 그대로), 기본 시점 난바, 전체 지도 fit은 당일치기 지역에 따라 확장, 공항→난바 라피트 동선, 지명 라벨 `PLACES` 간사이.
- 항공편: 간사이공항은 키 없는 공개 운항 정보 API가 없다(서버 렌더링 HTML, 비브라우저 403). `FLIGHT_API=false`로 "불러오기" 버튼을 숨기고 **공항 운항 현황 페이지 딥링크**(당일)만 표시. Worker `/flights`는 홍콩공항 전용이라 VER 2에서는 쓰지 않는다. 스카이스캐너 링크는 icn/kix.
- 장소 사전 `data/places-kansai.json`(형식 v2 `[ko,en,ja,lat,lng,kind,pop,cuisine,kosrc]`, 3번째 칸이 일본어). 2026-11-02 최종본 55,564곳(명소 19.5k·식당 15.9k·동네 8.8k·카페 6.3k·쇼핑 1.9k·교통 1.5k·호텔 1.2k·전망 459·페리 18), 한국어 표기 34.4k(AI 추정 `kosrc:ai` 33k), raw 5.1MB·gzip 1.28MB(GitHub Pages가 gzip 전송). 생성기 `tools/build_places.py`(핵심 bbox 5개 + 광역 bbox 4개 + 린쿠, Overpass 카테고리별 캐시 `tools/places_raw_kansai/`(git 제외) + Wikidata SPARQL 명소 보강(사이트링크 수→pop) + 丁目·잡음 필터 + 토끼(haiku)로 한국어 표기, 상한 35k) → 후처리 `tools/fix_places.py`(체인 상점→쇼핑, `;` 대안 표기 정리, 300m 안 같은 이름 중복 제거, 표기 오류 수동 보정 `KO_FIX`). 재생성 시 두 단계를 순서대로 실행한다. 식당·카페의 한국어 표기는 유명·체인 위주라 나머지는 영문·일본어로 검색된다. 검색 보조어 `KO_SYN`·동네 `AREA_PTS`·종류 `KIND_WORDS` 간사이판. Nominatim viewbox 134.85,34.15~136.10,35.25, 구글지도 검색어 접미사는 `regionEn()`(Osaka/Kyoto/Nara/Kobe).
- 아이콘: `icons/icon.svg`(소 + 토끼), PNG는 Chrome headless 렌더 + PIL. 헤더에도 `#cow` 심볼이 토끼 옆에 보인다(`.hero .cow`).
- 추천 여정 A/B/C·운영 정보 `INFO`·`EXTRA`·`HOTEL`은 오사카판으로 교체(`INFO_ASOF` 참고). `PLAN_U`는 날짜·항공편·숙소가 채워진 뼈대.

## 산출물·운영 (VER 1과 같음)
- `index.html` 단일 파일 앱. 배포: GitHub Pages https://minsukwkd-hub.github.io/palgoe-osaka/ (이 저장소 `main` 루트).
- `suzi-proxy/` Cloudflare Worker는 **VER 1과 공용**(https://suzi-proxy.suzi-proxy.workers.dev/, 도쿄 고정, `ALLOWED_ORIGIN`은 origin 단위라 추가 설정 불필요). 공유 코드 KV·사진 R2도 공용. Worker 코드를 고칠 때는 VER 1 저장소에서 고치고 배포한 뒤 이쪽에 복사한다.
- 설계 문서 `docs/설계.md`는 VER 1의 것을 그대로 가져왔다(데이터 모델·공유 포맷은 동일). 작업 기록은 `docs/작업기록.md`(VER 2부터 새로 시작).
- 파일이 크다(≈400KB). 편집은 정확한 문자열 치환으로 하고, 끝나면 `<script>` 본문을 `new Function`으로 문법 검사한다.

## 작업 규칙
- UI/UX 뼈대(색·폰트·레이아웃·시트 방식)는 VER 1에서 확정됨. 기능은 더하되 모양을 바꾸지 않는다.
- 이 폴더는 독립 git 저장소(GitHub `minsukwkd-hub/palgoe-osaka`, 공개). 회사 GitLab·다른 저장소는 절대 건드리지 않는다. VER 1 저장소(`C:\ClaudeTokki`)는 보존용이라 기능 변경 금지.
- 공개 저장소이므로 API 키·이메일·계정 ID를 커밋하지 않는다. 비밀은 Worker Secret에만.
- 운영 정보(`INFO`)는 웹 검증 날짜를 `INFO_ASOF`로 표시한다. 값이 바뀌면 `src`·`upd`·`conf`도 함께 갱신.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- 로컬 확인: `python -m http.server 8765 --directory .` 후 http://localhost:8765/index.html
