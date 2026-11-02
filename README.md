# 팔괴 여정 — 오사카 3박 4일 (2026.12.18 ~ 12.21)

어른 다섯, 아이 둘, 일곱 식구의 오사카 겨울 여행 페이지입니다. 휴대폰에서 보는 단일 `index.html`로 동작하며 GitHub Pages로 배포합니다.

"토끼의 여정" VER 1(홍콩 편, https://github.com/minsukwkd-hub/moneyeo-hongkong , 태그 `v1-hongkong`)을 바탕으로 만든 **VER 2**입니다. 홍콩 편은 그대로 보존하고, 이 저장소에서 오사카 편을 이어 갑니다.

- 여정 4종(당신의 여정 · 첫 번째 · 두 번째 · 세 번째) 버튼 전환, 직접 꾸미기(장소 넣기 — 오사카·교토·나라·고베 장소 사전 55,000여 곳, 한국어·영어·일본어로 검색)
- 장소별 설명·영업시간·요금·지도(정보 기준일 표시), 교토·나라·고베 당일치기 표시
- 토끼 여행 도우미(물어보기 버튼은 "시우·재이에게 물어보기"): claude.ai 아티팩트 안에서는 자동 연결, 밖에서는 `suzi-proxy/` 서버(VER 1과 공용)로 연결
- 다녀옴·메모·지출(¥·₩)·일기 기록, 사진·영상(기기 안 저장), 공유 링크·짧은 공유 코드

배포 주소: https://minsukwkd-hub.github.io/palgoe-osaka/

배포: `main` 브랜치 루트를 GitHub Pages로 게시. `index.html`을 고쳐 `git push`하면 1~2분 뒤 자동 반영됩니다.

로컬 확인: `python -m http.server 8765 --directory .` 후 http://localhost:8765/index.html
