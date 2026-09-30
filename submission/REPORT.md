# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Tống Trần Tiến Dũng
- **MSSV:** 2A202602791
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/Tiendung3tzz/K4-L3-DAY13-TongTranTienDung-2A202602791-Monitoring-LLMOps
- **Commit SHA cuối được đối chiếu:** `5ee161680771142a738f16e55615944caffb5aac`
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Project Langfuse cá nhân:** `day13-k4-l3b-2A202602791`

SHA ở trên là `HEAD` tại thời điểm đối chiếu source và evidence. File báo cáo này được hoàn thiện sau đó; khi commit thay đổi cuối cùng, cần thay dòng SHA bằng SHA mới của commit chứa báo cáo.

## 2. Evidence index

Các đường dẫn dưới đây là đường dẫn tương đối từ thư mục `submission/`.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08a-trace-metadata.png`, `evidence/08b-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt promote | `evidence/10a-prompt-rollback.png` |
| Prompt rollback | `evidence/10b-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả baseline và kết quả cuối

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---:|---:|---|
| `validate_logs.py` | 30/100 | 100/100 | Required fields và enrichment thiếu 0; PII leak 0; 10 correlation ID trong evidence validator. |
| `validate_dashboard.py` | 6/6 | 6/6 | Đủ sáu panel theo `config/dashboard.yaml`. |
| `pytest` | 22 tests | 24 tests collected; 17 passed, 3 failed, 4 errors | Hai test PII mới cho CCCD và thẻ. Các failure/error của full suite trong môi trường Windows hiện tại liên quan quyền thư mục tạm `WinError 5`; targeted CP2/PII tests đạt 12 passed, 1 deselected. |
| Số traces hợp lệ | 0 | Tối thiểu 10 trace trong project cá nhân | Evidence trace list có root/child observations; không dùng trace của project khác. |
| Số PII leak | 0 | 0 | Log và trace preview đều được redacted. |
| Latency P95 / TTFT P95 | 1593 ms / 51 ms | 2887 ms / 50 ms | Dashboard 60 phút; challenge có P99 4424 ms và request đại diện 4424 ms. |
| Retrieval success rate | Chưa có baseline contract | 100% | Không có retrieval failure trong workload/evidence challenge. |

Snapshot dashboard cuối trong `evidence/11-dashboard-overview.png`: 48 requests, error rate 0%, retrieval success 100%, cost tổng `$0.102633`, input/output tokens `2281/6386`, quality mean `0.8750`.

## 4. Logging và PII

### Correlation ID và structured logging

`CorrelationIdMiddleware` xóa structlog context cũ trước mỗi request. Middleware nhận `x-request-id` nếu header được gửi vào; nếu không có thì sinh ID dạng `req-<8-hex>`. ID được bind vào context, trả lại qua response header `x-request-id`, và context được xóa ở `finally` để tránh rò dữ liệu giữa hai request.

Trước event `request_received`, `app/main.py` bind các field:

- `user_id_hash` — SHA-256 rút gọn 12 ký tự, không ghi user ID thô;
- `session_id`;
- `feature`;
- `model`;
- `env`.

Các event chính là `request_received`, `response_sent` và `request_failed`. Response có thêm `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name` và `tool_success` để dashboard có thể tính latency, token, cost, quality và retrieval success.

### PII

`scrub_event` được đăng ký sau `format_exc_info` nhưng trước `JsonlFileProcessor` và JSON renderer. Vì vậy dữ liệu được scrub ở mọi field lồng nhau trước khi serialize hoặc ghi xuống `data/logs.jsonl`.

Các pattern đang có gồm email, số điện thoại Việt Nam, CCCD 12 chữ số và thẻ thanh toán 16 chữ số có thể có dấu cách hoặc dấu gạch nối. Tôi bổ sung test riêng cho CCCD và hai dạng thẻ trong `tests/test_pii.py`; không thay đổi yêu cầu rằng PII phải được redacted trước khi ghi.

Kết quả kiểm chứng: `validate_logs.py` đạt `100/100`; evidence 04 cho thấy structured log có correlation ID/enrichment; evidence 05 cho thấy email, phone, CCCD và credit card đã thành `[REDACTED_*]`.

## 5. Tracing và prompt versioning

### Trace

Starter root observation được mở rộng bằng Langfuse Python SDK v4:

```text
day13-agent-request
└── lab-agent-run
    ├── retrieval    (retriever observation)
    └── generation   (generation observation)
```

`LabAgent.run` dùng observation `lab-agent-run`; `retrieve` dùng child observation `retrieval`; `FakeLLM.generate` dùng child observation `generation`. Input/output raw không được capture. Chỉ ghi preview đã scrub, `doc_count`, model, usage và cost.

`correlation_id` được truyền trong `propagate_attributes` và metadata của trace. Vì vậy có thể lấy ID từ log, tìm trace tương ứng rồi so sánh waterfall. Evidence 07 cho thấy root `lab-agent-run` có hai child span. Evidence 06 cho thấy workload đã tạo nhiều trace/observation trong project cá nhân.

Trace incident được đối chiếu trực tiếp giữa evidence 13 và 14:

- `correlation_id`: `req-4d0820e1`;
- trace ID: `05b9cf5c3fc41798163fca9ea3a163f6`;
- root `lab-agent-run`: `4.43s`;
- `retrieval`: `2.50s`;
- `generation`: `0.15s`.

### Prompt version

Tôi tạo một prompt text duy nhất tên `day13-chat`, có đủ ba biến `{{feature}}`, `{{docs}}`, `{{message}}`.

- Version `#1`: label `baseline` và `production`.
- Version `#2`: thay đổi nhẹ format câu trả lời và label `candidate`.
- Evidence 09 xác nhận hai version và ba biến.
- Evidence 10a xác nhận promote: `production` chuyển sang version `#2`.
- Evidence 10b xác nhận rollback: `production` quay về version `#1`.

App chỉ gọi Langfuse theo `LANGFUSE_PROMPT_NAME` và `LANGFUSE_PROMPT_LABEL`; version không hard-code. Evidence 08a và 14 cho thấy metadata thực tế `prompt_name=day13-chat`, `prompt_label=candidate`, `prompt_version=2`, `prompt_source=langfuse`, không có `prompt_fetch_error`.

Trace ID của request candidate được ghi nhận ở trên. Evidence hiện có chưa mở riêng một trace v1 với trace ID hiển thị rõ; tôi không tự suy đoán hoặc điền trace ID không có trong ảnh. Đây là hạn chế evidence cần bổ sung nếu yêu cầu chấm bắt buộc phải có một trace ID riêng cho cả v1 và v2.

## 6. Dashboard, SLO, error budget và alerts

Dashboard runtime đọc `data/logs.jsonl`, time range 60 phút và refresh 30 giây. Sáu panel là:

| Panel | Dữ liệu và đơn vị | Threshold |
|---|---|---|
| Latency percentiles and TTFT | P50/P95/P99/TTFT P95, `ms` | P95 `<= 3000 ms` |
| Request traffic | request rate, `requests_per_minute` | rate `>= 1` |
| Error rate and retrieval success | error rate và retrieval success, `%` | error rate `<= 2%` |
| Cost over time | tổng/trung bình cost, `usd` | total `<= 2.5` |
| Input and output tokens | input/output token sum, `tokens` | sum `<= 50000` |
| Quality proxy | quality mean, `score_0_to_1` | mean `>= 0.75` |

`validate_dashboard.py` kiểm tra contract và đạt `HỢP LỆ: 6/6`. Evidence 11 là snapshot runtime có tên panel, đơn vị, threshold và time range. Evidence 12 bổ sung latency timeline để nhìn đoạn baseline và đoạn bất thường trên cùng trục thời gian.

### SLO và error budget

SLO chính là `fast_successful_requests` trong cửa sổ 28 ngày, target `99.5%`. Một request tốt phải có `response_sent` và `latency_ms <= 3000`; tổng mẫu lấy từ `request_received`. Error budget là `100% - 99.5% = 0.5%`. Với 10.000 request, ngân sách tối đa là 50 request không đạt SLO. Guardrails phụ gồm error rate tối đa 2%, daily cost tối đa `$2.5`, quality mean tối thiểu `0.75` và retrieval success tối thiểu `90%`.

### Alerts và runbook

Ba alert đều có duration 5 phút, owner `student-2A202602791`, kênh Slack `#k4-l3b-alerts` và runbook trong `docs/alerts.md`:

1. `HighLatencyP95` — warning khi `p95(response_sent.latency_ms) > 3000` trong 5 phút; runbook `docs/alerts.md#alert-1`.
2. `HighErrorRate` — critical khi `error_rate_pct > 2` trong 5 phút; runbook `docs/alerts.md#alert-2`.
3. `LowRetrievalSuccess` — warning khi `retrieval_success_rate_pct < 90` trong 5 phút; runbook `docs/alerts.md#alert-3`.

Runbook thống nhất quy trình Metrics → Logs → Traces trước khi mitigation: xác nhận panel và time range, lọc log theo UTC/correlation ID, sau đó mở trace cùng correlation ID.

## 7. Chuỗi điều tra incident

- **Challenge:** `day13-k4-l3b-monitoring-llmops-v1`, incident `rag_slow`, seed `1312`.
- **Metrics:** Evidence 12 cho thấy baseline khoảng `400–1000 ms`, sau đó latency tăng lên vùng `2650–4424 ms`; P95 dashboard là `2887 ms`, P99 là `4424 ms`, TTFT P95 vẫn `50 ms`. Dashboard threshold là `3000 ms`; challenge trigger là `2000 ms`, nên các điểm 2650–3000 ms vẫn là bất thường theo challenge dù chưa vượt threshold dashboard.
- **Logs:** Từ evidence 13 chọn request `response_sent` lúc `2026-09-30T16:11:13.715104Z`, `correlation_id=req-4d0820e1`, `latency_ms=4424`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`, `feature=qa`, `session_id=s01`.
- **Traces:** Evidence 14 mở đúng trace `05b9cf5c3fc41798163fca9ea3a163f6` có metadata `correlation_id=req-4d0820e1`. Waterfall cho thấy `retrieval` mất `2.50s`, còn `generation` chỉ `0.15s`; root mất `4.43s`.
- **Root cause:** `rag_slow` làm retrieval chậm khoảng 2.5 giây; bằng chứng metrics, log và trace cùng chỉ vào retrieval chứ không phải TTFT/generation.
- **Fix action:** Sau workload, tắt incident bằng `python scripts/inject_incident.py --disable`; health check xác nhận `rag_slow=false`, `tool_fail=false`, `cost_spike=false`.
- **Preventive measure:** Giữ `HighLatencyP95`, lọc correlation ID theo time range, bắt buộc đối chiếu retrieval/generation span trước khi rollback hoặc mitigation; bổ sung regression test cho latency của retrieval.

## 8. Giải thích và tự đánh giá

### Quyết định kỹ thuật

Quyết định quan trọng nhất là đặt PII scrubber trước file writer và JSON renderer, đồng thời đặt `capture_input=False` và `capture_output=False` cho observation. Lý do là log/trace vẫn cần correlation ID, metadata, token và cost để điều tra, nhưng không được đánh đổi bằng raw message hoặc raw answer có thể chứa email, phone, CCCD hay thẻ. Preview dùng `summarize_text` sau redaction để giữ khả năng tìm kiếm an toàn.

### Lỗi/blocker và cách xử lý

Full pytest trong Windows execution environment gặp `WinError 5: Access is denied` khi pytest tạo/dọn thư mục tạm. Tôi tách kết quả: ghi nhận chính xác `24 collected, 17 passed, 3 failed, 4 errors`, chạy lại nhóm test CP1/CP2/PII độc lập để kiểm tra assertion ứng dụng, và không biến lỗi quyền môi trường thành kết luận rằng PII/tracing/dashboard implementation sai. Hạn chế này được ghi trong evidence `01-pytest.txt` và bảng kết quả.

### Metrics → Logs → Traces

Metrics trả lời “panel nào bất thường và lúc nào”; trong incident này latency tăng trong đoạn challenge nhưng TTFT không tăng. Logs thu hẹp phạm vi bằng UTC timestamp và cho biết request cụ thể qua `correlation_id=req-4d0820e1`. Trace dùng chính correlation ID đó để mở waterfall, xác định `retrieval` là span chậm. Không mở trace ngẫu nhiên và không kết luận root cause chỉ từ thời gian client của `load_test.py`.

### Vai trò của prompt, token/cost, SLO và rollback

Prompt label tách việc phát hành khỏi code: app luôn hỏi Langfuse theo name/label, nên promote hoặc rollback chỉ là đổi label `production`. Version và label trong metadata giúp so sánh v1/v2. Token usage và cost của generation là tín hiệu để phát hiện prompt dài hoặc cost spike. SLO biến mức “chậm/lỗi” thành error budget có thể theo dõi. Rollback đưa `production` về version đã biết ổn định khi candidate gây regression.

### Điều học được và hạn chế còn lại

Tôi học được rằng correlation ID nối các log của một request, còn trace ID nối các observation trong trace; P95/P99 quan trọng hơn average khi điều tra tail latency; và redaction phải xảy ra trước serialize. Hạn chế còn lại là full pytest bị ảnh hưởng bởi ACL thư mục tạm, dashboard hiện là HTML local chứ chưa phải hệ thống alert production, Slack alert mới ở mức contract/runbook, và evidence hiện chưa có một trace v1 riêng với trace ID hiển thị rõ.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence đã được đối chiếu với source tại commit `5ee161680771142a738f16e55615944caffb5aac`.
- [x] Evidence 01–14 có đường dẫn tương đối trong report; pytest dùng output text theo hướng dẫn evidence.
- [x] Incident evidence nối đúng metric → log → trace bằng `correlation_id=req-4d0820e1`.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và không chụp API secret.
- [x] Repository chạy lại được theo README cho các validator và workload chính.
- [x] Không đưa secret, API key hoặc PII thô vào report/evidence.
- [ ] Nếu yêu cầu chấm bắt buộc hai trace ID prompt riêng biệt, bổ sung trace v1 vào evidence và cập nhật mục 5.
- [ ] Sau khi commit thay đổi `REPORT.md` và `01-pytest.txt`, cập nhật lại Commit SHA ở mục 1.
