# kospi-data
코스피·코스닥 일간 시세를 GitHub Actions로 매일 자동 수집합니다 (평일 16:40 KST, 다음날 07:30 KST 백업).
- `data/kospi_daily.csv`: date, Open, High, Low, Close, Volume
- `data/kosdaq_daily.csv`
수동 실행: Actions 탭 → fetch-kospi → Run workflow.

## 연준(FOMC·연설) 원문
`fetch-fed` 워크플로가 매일 04:15·07:15 KST에 federalreserve.gov에서 FOMC 성명서와 연준 이사 연설 원문을 받아 `data/fed/`에 저장합니다.
- `data/fed/statements/YYYYMMDD.txt`, `index.json`
- `data/fed/speeches/*.txt`, `index.json` (최근 60일)
