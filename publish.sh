#!/usr/bin/env bash
# 주식 리포트를 GitHub(공개 저장소 stock-report)에 올리고 GitHub Pages 를 켭니다.
# 처음 한 번은 저장소를 만들고, 이후에는 변경분만 push 합니다.
set -e
GH="$(command -v gh || echo /c/Program Files/GitHub CLI/gh.exe)"
cd "$(dirname "$0")"

[ -d .git ] || git init -q -b main
printf 'kakao.txt\n__pycache__/\n' > .gitignore
git add -A
git -c user.name="Kkhgold" -c user.email="kkhssam3@gmail.com" commit -q -m "Stock report $(date +%Y-%m-%d)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || echo "(변경 없음)"

if ! git remote get-url origin >/dev/null 2>&1; then
  "$GH" repo create stock-report --public --source . --push --description "평일 9시 30분 주식 리포트"
  "$GH" api -X POST repos/Kkhgold/stock-report/pages -f "source[branch]=main" -f "source[path]=/" >/dev/null
else
  git push -q origin main
fi
echo "✅ https://kkhgold.github.io/stock-report/"
