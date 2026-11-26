# kospi-data
코스피·코스닥 일간 시세를 GitHub Actions로 매일 자동 수집합니다 (평일 16:40 KST, 다음날 07:30 KST 백업).
- `data/kospi_daily.csv`: date, Open, High, Low, Close, Volume
- `data/kosdaq_daily.csv`
수동 실행: Actions 탭 → fetch-kospi → Run workflow.

## 원자재·환율 (`fetch_macro.py`)
같은 워크플로가 `data/macro_daily.csv`도 갱신합니다 (2005년~, 일간 종가).
- 원자재: wti, brent (USD/배럴), natgas (USD/MMBtu), gold, silver (USD/온스), copper (USD/파운드), aluminum (USD/톤)
- 환율: usdkrw, eurkrw, cnykrw, jpykrw100 (원/100엔), usdjpy
- 출처: Yahoo Finance 선물·환율, 빈 날은 FRED 일간 계열로 채움. 원화 교차환율은 USD/KRW와 EUR/USD·USD/CNY·USD/JPY로 계산.
- 알루미늄 등 일간 이력이 짧은 금속은 그 이전을 FRED(IMF) 월평균으로 채움.
