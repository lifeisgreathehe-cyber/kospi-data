# kospi-data
코스피·코스닥 일간 시세를 GitHub Actions로 매일 자동 수집합니다 (평일 16:40 KST, 다음날 07:30 KST 백업).
- `data/kospi_daily.csv`: date, Open, High, Low, Close, Volume
- `data/kosdaq_daily.csv`
수동 실행: Actions 탭 → fetch-kospi → Run workflow.

## 원자재·환율 (`fetch_macro.py`)
같은 워크플로가 `data/macro_daily.csv`도 갱신합니다 (2005년~, 일간 종가).
- 원자재: wti, brent (USD/배럴), natgas (USD/MMBtu), gold, silver (USD/온스), copper (USD/파운드), aluminum (USD/톤)
- 환율: usdkrw, eurkrw, cnykrw, jpykrw100 (원/100엔), usdjpy
- 출처: Yahoo Finance 근월물 선물·환율 종가. FRED 일간 계열은 닿을 때만 빈 날을 채움(GitHub 러너에선 자주 시간 초과). 원화 교차환율은 USD/KRW와 EUR/USD·USD/CNY·USD/JPY로 계산.
- 알루미늄은 COMEX 선물이 거의 거래되지 않던 2020년 이전을 IMF 월평균(DBnomics)으로 채움. 하루만 튀었다 돌아오는 잘못된 시세는 걸러 냄.

## 나스닥100 CTA 포지셔닝 추정 (fetch-cta-ndx, 평일 07:30 KST)
골드만 'CTA Positioning in NDX Index'는 비공개라 공개 데이터로 만든 대체 지표입니다.
- `data/ndx_daily.csv`: ^NDX 종가
- `data/cta_ndx.csv`: 추세추종 모델(1·3·6개월 추세 신호, 변동성 목표 15%). `est_bn`은 골드만 차트 눈금(10억 달러)으로 환산한 추정치, `flip_*`은 각 신호가 바뀌는 NDX 가격
- `data/cftc_ndx.csv`: CFTC TFF 나스닥100(통합) 레버리지펀드·자산운용사 순포지션(주간)
