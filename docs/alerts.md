# Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighErrorRate
- Severity: P1
- SLI/SLO liên quan: `error_rate_pct` (SLO ≤ 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: request `/chat` trả lỗi 500, người dùng không nhận được câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Error rate & breakdown, xem `error_type` chiếm đa số (thường `RuntimeError` do tool_fail).
  2. Lọc log `event == "request_failed"`, lấy `correlation_id` một request lỗi.
  3. Mở trace theo correlation_id, xác định span RAG (`Vector store timeout`) hay LLM gây lỗi.
- Mitigation tạm thời: tắt incident/tool lỗi (`POST /incidents/tool_fail/disable`) hoặc bật fallback không dùng vector store; thông báo trạng thái.
- Owner: sre-oncall

## Alert 2

- Tên: HighLatencyP95
- Severity: P2
- SLI/SLO liên quan: `latency_p95_ms` (SLO ≤ 3000ms)
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: câu trả lời chậm, trải nghiệm chat giật/treo dù không lỗi
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency percentiles, xác nhận P95/P99 tăng còn P50 bình thường (đuôi latency).
  2. Mở trace của request chậm, so sánh thời lượng span `rag_retrieve` và `llm_generate`.
  3. Nếu span RAG ~2.5s → nghi `rag_slow`; kiểm tra log/incidents state.
- Mitigation tạm thời: tắt `rag_slow` (`POST /incidents/rag_slow/disable`), giảm concurrency, hoặc đặt timeout ngắn cho RAG.
- Owner: sre-oncall

## Alert 3

- Tên: DailyCostSpike
- Severity: P2
- SLI/SLO liên quan: `daily_cost_usd` (SLO ≤ 2.5 USD/ngày)
- Điều kiện và thời gian duy trì: `daily_cost_usd > 2.5` duy trì 10 phút
- Ảnh hưởng tới người dùng: không lỗi trực tiếp, nhưng đốt ngân sách và cảnh báo lạm dụng
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Cost over time và Tokens, xem `tokens_out` có tăng đột biến không.
  2. Lấy `correlation_id` request có cost cao, mở trace xem `usage_details`.
  3. Đối chiếu với incident `cost_spike` (output tokens ×4) trong log/state.
- Mitigation tạm thời: tắt `cost_spike`, đặt trần `max_tokens` cho LLM, bật rate limit theo user.
- Owner: platform-oncall
