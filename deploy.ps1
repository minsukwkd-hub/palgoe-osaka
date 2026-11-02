# GitHub Pages 배포 스크립트 (gh CLI 로그인 후 실행: .\deploy.ps1)
# 1) 공개 저장소 생성  2) 푸시  3) Pages 활성화(main 브랜치 루트)  4) 주소 출력
param([string]$Repo = "palgoe-osaka")
$ErrorActionPreference = "Stop"
gh auth status | Out-Null
$user = gh api user --jq .login
if (-not (gh repo view "$user/$Repo" 2>$null)) {
  gh repo create $Repo --public --source . --remote origin --push --description "엄마랑 딸, 천천히 홍콩 — 3박4일 여행 페이지"
} else {
  if (-not (git remote 2>$null | Select-String -SimpleMatch "origin")) { git remote add origin "https://github.com/$user/$Repo.git" }
  git push -u origin main
}
try { gh api -X POST "repos/$user/$Repo/pages" -f "source[branch]=main" -f "source[path]=/" | Out-Null } catch { }
gh api -X PUT "repos/$user/$Repo/pages" -f "source[branch]=main" -f "source[path]=/" | Out-Null
"배포 주소: https://$user.github.io/$Repo/   (처음엔 1~3분 뒤 열려요)"
