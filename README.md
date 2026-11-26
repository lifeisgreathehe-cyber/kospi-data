# kospi-data
코스피·코스닥 일간 시세를 GitHub Actions로 매일 자동 수집합니다 (평일 16:40 KST, 다음날 07:30 KST 백업).
- `data/kospi_daily.csv`: date, Open, High, Low, Close, Volume
- `data/kosdaq_daily.csv`
수동 실행: Actions 탭 → fetch-kospi → Run workflow.

## 나스닥100 CTA 포지셔닝 추정 (fetch-cta-ndx, 평일 07:30 KST)
골드만 'CTA Positioning in NDX Index'는 비공개라 공개 데이터로 만든 대체 지표입니다.
- `data/ndx_daily.csv`: ^NDX 종가
- `data/cta_ndx.csv`: 추세추종 모델(1·3·6개월 추세 신호, 변동성 목표 15%). `est_bn`은 골드만 차트 눈금(10억 달러)으로 환산한 추정치, `flip_*`은 각 신호가 바뀌는 NDX 가격
- `data/cftc_ndx.csv`: CFTC TFF 나스닥100(통합) 레버리지펀드·자산운용사 순포지션(주간)
