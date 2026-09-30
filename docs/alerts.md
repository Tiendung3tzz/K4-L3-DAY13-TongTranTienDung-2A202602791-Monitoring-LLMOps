# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 trong SLO `fast_successful_requests`
- Điều kiện và thời gian duy trì: `p95(response_sent.latency_ms) > 3000` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu trước khi nhận câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency, xác nhận P95/P99 và TTFT trong cùng time range.
  2. Lọc `data/logs.jsonl` theo `response_sent.latency_ms > 3000`, lấy `correlation_id` đại diện.
  3. Mở trace cùng `correlation_id`, so sánh thời lượng retrieval và generation.
- Mitigation tạm thời: giảm tải, tắt practice incident hoặc rollback prompt production nếu generation tăng bất thường.
- Owner: `student-2A202602791`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: error rate guardrail tối đa 2% và SLO request thành công.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` trong 5 phút.
- Ảnh hưởng tới người dùng: request có thể trả lỗi hoặc không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors, xem error rate và breakdown theo `error_type`.
  2. Lọc các event `request_failed`, kiểm tra `tool_name`, `tool_success` và `correlation_id`.
  3. Mở trace lỗi tương ứng để xác định retrieval hay generation là bước thất bại.
- Mitigation tạm thời: khôi phục dependency lỗi, tắt incident đang bật và rollback cấu hình/prompt mới nếu có liên quan.
- Owner: `student-2A202602791`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: retrieval success rate tối thiểu 90%.
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90` trong 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu context hoặc rơi vào fallback.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors và tính `tool_success == true` trên mọi event có `tool_success`.
  2. Lọc các request có `tool_success: false`, lấy `correlation_id` và query preview đã scrub.
  3. Mở trace để kiểm tra retrieval span, timeout và số document trả về.
- Mitigation tạm thời: khôi phục vector store, tắt `tool_fail`/practice incident hoặc chuyển sang fallback có kiểm soát.
- Owner: `student-2A202602791`
