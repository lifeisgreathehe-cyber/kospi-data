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
## ISM PMI (제조업·서비스, 구성항목 포함)
- `data/pmi/ism_monthly.csv`: month, m_* (제조업 PMI·신규주문·생산·고용·공급자배송·재고·고객재고·가격·수주잔고·신규수출주문·수입), s_* (서비스 PMI·사업활동·신규주문·고용·공급자배송·재고·가격·수주잔고·신규수출주문·수입·재고체감). 2005년~.
- `data/pmi/reports.jsonl`: ISM 월간 보고서 'AT A GLANCE' 표를 읽은 기록(웹 아카이브의 ism.ws·instituteforsupplymanagement.org·ismworld.org, PR Newswire). 값은 발표 당시 기준(이후 계절조정 개정 미반영).
- GitHub Actions `fetch-pmi`가 매월 1~9일 하루 두 번 PR Newswire의 ISM 보도자료(대체: ismworld.org)를 읽어 새 달을 더합니다.
