# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên: Tống Trần Tiến Dũng**
- **MSSV: 2A202602791**
- **Lớp:** K4-L3B
- **Repository URL:https://github.com/Tiendung3tzz/K4-L3-DAY13-TongTranTienDung-2A202602791-Monitoring-LLMOps**
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-<MSSV>`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08a-trace-metadata.png`,`evidence/08b-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10a-prompt-rollback.png`, `evidence/10b-prompt-rollback.png`|
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Required/enrichment thiếu 0, PII leak 0 |
| `validate_dashboard.py` | 6/6 | 6/6 | Dashboard contract hợp lệ |
| `pytest` | 22 tests | 24 tests collected | Local sandbox còn lỗi quyền thư mục temp; không phải lỗi assertion CP2 |
| Số traces hợp lệ | — | Chưa xác minh cloud | Đã chạy workload; cần đối chiếu trace list Langfuse khi endpoint hoạt động |
| Số PII leak | 0 | 0 | Đạt |
| Latency P95 / TTFT P95 | 1593 ms / 51 ms | 3640 ms / 50 ms | Challenge `rag_slow` làm latency vượt ngưỡng 2000 ms |
| Retrieval success rate | — | 100% | Không có retrieval failure |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
- **Các metadata được ghi vào structured log:**
- **Cách bảo đảm PII được scrub trước khi ghi:**
- **Cách kiểm chứng kết quả:**

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` (`rag_slow`, seed `1312`).
- **Khoảng thời gian điều tra:** `2026-09-30T05:17:56Z`–`2026-09-30T05:18:11Z` (UTC).
- **Triệu chứng từ metrics:** Baseline có latency P95 `1593 ms`, TTFT P95 `51 ms`. Challenge mới nhất có latency P95 `3640 ms`, vượt threshold `2000 ms` và tăng `2047 ms` (~2.29x); TTFT P95 vẫn `50 ms`, retrieval success `100%`.
- **Log line và correlation ID liên quan:** `response_sent` lúc `2026-09-30T05:17:59.857925Z`, `correlation_id=req-484912de`, `latency_ms=3640`, `tool_name=retrieval`, `tool_success=true`, feature `monitoring`.
- **Trace ID và span gây ảnh hưởng:** Chưa xác minh được do endpoint Langfuse timeout; cần mở trace có `correlation_id=req-484912de` và ghi trace ID cùng span `retrieval` vào đây.
- **Root cause:** Provisional: challenge `rag_slow` làm retrieval chậm khoảng 2.5 giây; cần bổ sung trace waterfall để hoàn tất bằng chứng thứ ba.
- **Fix action:** Đã tắt incident sau workload bằng `python scripts/inject_incident.py --disable`; health check xác nhận cả ba incident đều `false`.
- **Preventive measure:** Giữ alert `HighLatencyP95` ở P95 `>3000 ms` trong `5m`, lọc log theo `correlation_id`, sau đó đối chiếu retrieval/generation span trước khi rollback hoặc mitigation.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
