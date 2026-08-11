# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Pistachio-Big (K3) — _đổi nếu tên nhóm khác_
- Repository URL: https://github.com/Pistachio-Big/Day13-K3-Observability-Funny
- Commit SHA cuối: `0fea9d22ddaec3514da2d97bb8e4d7b03e0fe611`
- Thành viên và vai trò:
  - Hoàng Văn Phái (2A202601575) — A: API & Middleware
  - Nguyễn Huy Anh (2A202601641) — B: Security / PII
  - Phạm Trung Kiên (2A202601986) — C: Metrics & Dashboard
  - Hà Tấn Phong (2A202601577) — D: SRE & Alerts
  - Nguyễn Văn Đại (2A202601217) — E: QA & Chief Investigator (Langfuse, tracing, điều tra)

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** (baseline ban đầu 30/100)
- Tổng số traces: ≥ 40 trace trên Langfuse (10 baseline + 10 candidate + 10 challenge + các lần practice), mỗi trace có waterfall `run → rag_retrieve + llm_generate`
- Số PII leak còn lại: **0** (email/SĐT/CCCD/thẻ đều `[REDACTED_*]`)
- Link/đường dẫn dashboard: `submission/evidence/cp2_dashboard.png` (baseline) và `submission/evidence/cp3_dashboard_incident.png` (lúc sự cố), sinh bằng `scripts/build_dashboard.py`; contract `python scripts/validate_dashboard.py` → `6/6 panel`

## 3. Logging và tracing

- Evidence correlation ID: `cp1_response_headers.txt` (header `x-request-id` + `x-response-time-ms`) và `cp1_log_enriched.txt` (log `response_sent` có `correlation_id` + đủ enrichment)
- Evidence PII redaction: `cp1_pii_redacted.txt` (log đã che email/SĐT/thẻ) và `cp1_validate_logs.txt` / `cp1_validate_100.png` (100/100)
- Evidence trace waterfall: `cp2_trace_baseline.png` — trace `run` gồm span con `rag_retrieve` và `llm_generate`
- Giải thích một span đáng chú ý: span **`rag_retrieve`** — lúc bình thường ~0ms, khi sự cố `rag_slow` bật thì lên **2505ms** trong khi `llm_generate` vẫn 151ms; chính span này giúp khoanh vùng root cause ở CP3 (xem §6)

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: v1 — labels `production`, `baseline`
- Version/label candidate: v2 — label `candidate` (thêm dòng "Answer concisely in at most 3 sentences.")
- Trace ID của mỗi version:
  - Baseline (v1, `prompt_label=baseline`, `prompt_source=langfuse`): `6e1b16181af80117ef79f980b55bf80f`
  - Candidate (v2, `prompt_label=candidate`, `prompt_source=langfuse`): `50650462c05fe1bd5f109c8f65ac3818`
- Bằng chứng đổi label hoặc rollback: `submission/evidence/cp2_rollback_before.png` (production→v2) và `submission/evidence/cp2_rollback_after.png` (rollback production→v1) — _làm Phần 3.3 rồi chụp_
- Evidence khác: `cp2_prompt_versions.png` (2 version + label), `cp2_trace_baseline.png` (metadata trace baseline)

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard: `submission/evidence/cp2_dashboard.png` — 6 panel (latency, traffic, errors, cost, tokens, quality) sinh từ `data/logs.jsonl` bằng `scripts/build_dashboard.py`, có time range 60m, đơn vị và đường threshold/SLO (nét đứt đỏ) trên mỗi panel.
- SLO đã chọn và lý do (theo `config/slo.yaml`):
  - `latency_p95_ms ≤ 3000` — mức chờ tối đa người dùng chat còn chấp nhận cho câu trả lời có RAG.
  - `error_rate_pct ≤ 2` — vượt là dấu hiệu tool_fail/lỗi hệ thống ảnh hưởng trực tiếp người dùng.
  - `daily_cost_usd ≤ 2.5` — chặn cost_spike (output tokens tăng đột biến) đốt ngân sách.
  - `quality_score_avg ≥ 0.75` — ngưỡng chất lượng trả lời tối thiểu.
- Alert rules và runbook (`config/alert_rules.yaml` + `docs/alerts.md`):
  - `HighErrorRate` (P1): `error_rate_pct > 2` trong 5m.
  - `HighLatencyP95` (P2): `latency_p95_ms > 3000` trong 5m.
  - `DailyCostSpike` (P2): `daily_cost_usd > 2.5` trong 10m.
  - Mỗi alert dựa triệu chứng/SLO, có runbook đầy đủ (ảnh hưởng, 3 bước kiểm tra, mitigation, owner) tại `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (cohort K3, incident `rag_slow`, feature `refund`, ngưỡng 2000ms)
- Triệu chứng từ metrics: sau khi chạy `load_test --challenge`, `latency_p50` nhảy từ **151ms → 2651ms**, `p95` vượt cả ngưỡng challenge 2000ms lẫn SLO dashboard 3000ms; `error_rate_pct = 0%` và token/cost không đổi → chỉ **latency tăng**, khu trú ở feature `refund`. Panel Latency trên dashboard (`cp3_dashboard_incident.png`) chạm ngưỡng đỏ.
- Trace ID liên quan: `0e69a3723bbf55247140f649f83a5ee7` (session `k3-challenge-s05`, total 2.66s). Trong waterfall: span **`rag_retrieve` = 2505ms** trong khi **`llm_generate` = 151ms** (không đổi) → nút thắt nằm ở bước RAG, không phải LLM.
- Log line/correlation ID liên quan: `req-240004f4` → `response_sent` `feature=refund` `latency_ms=2652` (đối chứng request lành mạnh `req-046cad7f` cùng feature chỉ `latency_ms=151`).
- Root cause: sự cố `rag_slow` khiến `retrieve()` chạy `time.sleep(2.5)` ở [app/mock_rag.py:17-18](../app/mock_rag.py) cho mọi request khi `STATE["rag_slow"]` bật → mỗi truy vấn refund bị cộng thêm ~2.5s ở bước truy hồi tài liệu.
- Fix action: tắt sự cố `POST /incidents/rag_slow/disable` (đã xác nhận metrics về 151ms); trong hệ thống thật: sửa/nâng vector store chậm và **đặt timeout ngắn cho RAG** để fail-fast thay vì chờ 2.5s.
- Preventive measure:
  1. Timeout + fallback cho bước RAG (không để 1 dependency chậm kéo toàn bộ latency).
  2. Alert `HighLatencyP95` (`latency_p95_ms > 3000` trong 5m) đã cấu hình sẵn → phát hiện tự động; kèm dashboard có SLO line.
  3. Giữ span riêng `rag_retrieve`/`llm_generate` (đã thêm ở CP2) để lần sau khoanh vùng nút thắt trong vài giây.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng. Cột "Điều đã học" là gợi ý theo vai trò — mỗi người chỉnh lại theo ý mình.

| Thành viên (MSSV) | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Hoàng Văn Phái (2A202601575) | A — Middleware, correlation ID `req-<8hex>`, enrich log, exception handler; điều tra CP3 (đối chiếu correlation_id log↔trace↔metrics) | PR #1 · `a1b7b35` | Correlation ID + contextvars giúp truy vết một request xuyên suốt log |
| Nguyễn Huy Anh (2A202601641) | B — PII scrubbing, thêm regex passport/địa chỉ, đăng ký processor; điều tra CP3 (dùng log chứng minh latency) | PR #2 · `dda429b` | Redact PII ở tầng processor đảm bảo không lộ dữ liệu dù log ở đâu |
| Phạm Trung Kiên (2A202601986) | C — `error_rate_pct`, spec dashboard 6 panel; điều tra CP3 (đọc metrics ra triệu chứng) | PR #3 · `ddbcf8d` | Cách tính error_rate_pct và đọc percentile p50/p95/p99 |
| Hà Tấn Phong (2A202601577) | D — SLO, 3 alert rules, runbook; điều tra CP3 (đề xuất fix + preventive) | PR #4 · `372bc36` | Alert nên dựa triệu chứng/SLO và kèm runbook để xử lý nhanh |
| Nguyễn Văn Đại (2A202601217) | E — Langfuse, span trace RAG/LLM, prompt v1/v2 + rollback, dashboard runtime, dẫn dắt điều tra CP3, tổng hợp report | PR #5 · `bd5234b`; PR #6 · `a860b9d` | Luồng Metrics→Traces→Logs và prompt versioning/rollback trên Langfuse |
