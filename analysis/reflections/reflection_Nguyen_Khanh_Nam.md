# Báo cáo Cá nhân - Lab 14

**Họ và tên**: Nguyễn Khánh Nam
**MSSV**: 2A202600172
**Vai trò**: R5 — AI Engineer (Judge-Gemini + Agent V2)

---

## 1. Tổng quan vai trò và nhiệm vụ đã thực hiện

Trong Lab 14, tôi đảm nhiệm vai trò AI Engineer phụ trách phát triển Judge-Gemini (Gemini 1.5 Pro), cải tiến Agent V2, và dẫn dắt phân tích lỗi (Failure Analysis). Nhiệm vụ cụ thể gồm:

- Xây dựng logic Judge sử dụng Gemini 1.5 Pro, tích hợp vào llm_judge.py (phía Gemini).
- Thiết kế và triển khai Agent V2 trong main_agent.py với các cải tiến: reranker theo keyword overlap, prompt "only answer from context".
- Chủ trì phân tích lỗi, thực hiện Failure Analysis trong failure_analysis.md (5-Whys cho các case tệ nhất).
- Đóng góp vào logic Multi-Judge Consensus, xử lý position bias, và phối hợp với R4 để hoàn thiện rubric chấm điểm.

---

## 2. Phân tích kỹ thuật & bài học

### 2.1. Judge-Gemini & Multi-Judge Consensus

- Phát triển hàm đánh giá tự động bằng Gemini, đảm bảo so sánh chéo với GPT-4o.
- Đề xuất và triển khai logic agreement rate liên tục thay vì nhị phân, giúp đánh giá mức độ đồng thuận giữa các Judge chính xác hơn.
- Xử lý trường hợp chênh lệch điểm số lớn (|Δ| > 1) bằng cách gọi thêm model thứ ba (gpt-4o) làm trọng tài, chỉ escalate khi cần thiết để tối ưu chi phí.

### 2.2. Agent V2 & Position Bias

Thiết kế lại Agent V2 với reranker đơn giản (keyword overlap) để tăng độ chính xác truy xuất.
Áp dụng prompt nghiêm ngặt, buộc LLM chỉ trả lời dựa trên context cung cấp, giảm thiểu hiện tượng "hallucination".
Nghiên cứu và kiểm tra hiện tượng position bias, đề xuất hoán đổi vị trí các response khi chấm để Judge không bị ảnh hưởng bởi thứ tự.

### 2.3. Failure Analysis & Quy trình kiểm thử

Chủ động tổng hợp kết quả benchmark, xác định 3 case tệ nhất và thực hiện phân tích 5-Whys chi tiết.
Đề xuất cải tiến quy trình kiểm thử: chỉ escalate các case ambiguous hoặc điểm trung bình cho Judge cao cấp, tiết kiệm chi phí mà vẫn đảm bảo chất lượng.

---

# 3. Bài học rút ra

Tối ưu chi phí qua Judge Cascade: Không phải case nào cũng cần Judge cao cấp. Áp dụng workflow cascade giúp tiết kiệm ~80% chi phí mà không giảm chất lượng tổng thể.

Đồng thuận đa mô hình: Sử dụng nhiều Judge giúp giảm rủi ro sai lệch/hallucination của từng model riêng lẻ.
Tầm quan trọng của prompt và kiểm soát context: Prompt rõ ràng, kiểm soát context đầu vào là chìa khóa để LLM trả lời chính xác và an toàn.
Phối hợp nhóm & giải quyết conflict: Việc merge code Judge giữa R4 và R5 gặp xung đột, tôi đã phối hợp với R1 để giải quyết, đảm bảo pipeline hoạt động trơn tru.

---

# 4. Đóng góp nổi bật (kèm id commit)

[2e0971d] Phát triển Agent V2 với reranker và prompt mới trong main_agent.py.
[2e0971d] Tích hợp Judge-Gemini vào llm_judge.py, hoàn thiện logic consensus.
[2e0971d] Chủ trì Failure Analysis, viết báo cáo phân tích lỗi chi tiết.
[2e0971d] Tham gia giải quyết conflict khi merge Judge logic với R4.