# Yêu cầu dashboard

Contract có thể kiểm tra bằng máy nằm tại `config/dashboard.yaml`. Hướng dẫn dựng và kiểm tra runtime nằm tại [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md).

Dashboard chính cần đủ 6 nhóm thông tin:

1. Latency P50/P95/P99.
2. Traffic: request count hoặc QPS.
3. Error rate và breakdown theo loại lỗi.
4. Cost theo thời gian.
5. Tổng token input/output.
6. Quality proxy.

## Spec chi tiết 6 panel

Nguồn chuẩn của cả 6 panel là `data/logs.jsonl`; contract máy đọc nằm ở `config/dashboard.yaml`.

| # | Panel | Event nguồn | Field | Aggregation | Đơn vị | Threshold / SLO |
|---|---|---|---|---|---|---|
| 1 | Latency percentiles | `response_sent` | `latency_ms` | p50, p95, p99 | ms | p95 ≤ 3000 |
| 2 | Request traffic | `request_received` | `event` | count, rate_per_minute | req/phút | rate ≥ 1 |
| 3 | Error rate & breakdown | `request_received`, `request_failed` | `error_type` | `error_rate_pct`, count_by_value | percent | error_rate_pct ≤ 2 |
| 4 | Cost over time | `response_sent` | `cost_usd` | sum_by_minute, total | usd | total ≤ 2.5 |
| 5 | Input/Output tokens | `response_sent` | `tokens_in`, `tokens_out` | sum_by_field | tokens | sum ≤ 50000 |
| 6 | Quality proxy | `response_sent` | `quality_score` | mean | score 0–1 | mean ≥ 0.75 |

Ghi chú:

- `error_rate_pct = count(request_failed) / count(request_received) * 100` (khớp `app/metrics.py:error_rate_pct`).
- Mỗi panel phải hiển thị đường **threshold/SLO** tương ứng cột cuối để người xem thấy ngay vượt ngưỡng.
- 3 loại lỗi thường gặp trong breakdown: `RuntimeError` (tool_fail), timeout do `rag_slow`, và lỗi validate input (422).

Tiêu chuẩn trình bày:

- Khoảng thời gian mặc định: 1 giờ.
- Tự refresh mỗi 15–30 giây nếu công cụ hỗ trợ.
- Có threshold hoặc SLO line.
- Ghi rõ đơn vị.
- Chỉ giữ 6–8 panel quan trọng ở lớp chính.
- Screenshot phải nhìn được tên panel và khoảng thời gian.

Kiểm tra contract trước khi chụp evidence:

```bash
python scripts/validate_dashboard.py
```
