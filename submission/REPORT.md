# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

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

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
