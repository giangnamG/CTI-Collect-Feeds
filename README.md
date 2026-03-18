# CTI-Collect-Feeds

`sososo.py` là script crawl kết quả từ bot Telegram `@sososo`, chỉ trích xuất `title + link` và ghi kết quả thành các file JSON theo batch.

## Tính năng hiện có

- Gửi query tới `@sososo` qua `telegram-mcp`
- Crawl theo từng trang với `--max-page`
- Tách và dedupe `title + link`
- Ghi kết quả JSON theo batch với `--batch`
- Lưu file vào `batches/YYMMDD-HHMMSS/0001.json`
- Phát hiện challenge của bot theo kiến trúc detector mở rộng
- Hỗ trợ challenge phép tính có gợi ý đáp án
- Hỏi user xác nhận `y/n` sau khi giải challenge để tiếp tục crawl
- Console log màu theo từng bước và lưu file log vào `logs/sososo_logs`
- Kết thúc chương trình chỉ in summary ra console, không dump toàn bộ items

## Cách dùng

```powershell
python sososo.py --query "bank fake" --max-page 10 --batch 30
```

## Tham số chính

- `--query`: từ khóa cần crawl. Đây là tham số bắt buộc, ví dụ: `--query "bank fake"`.
- `--max-page`: số trang tối đa sẽ crawl. Đây là tham số bắt buộc, ví dụ: `--max-page 10`.
- `--batch`: số item trong mỗi file JSON. Giá trị phải là số nguyên lớn hơn hoặc bằng `1`. Mặc định: `50 item`.
- `--output-dir`: thư mục gốc để ghi `batches/` và `logs/`. Mặc định: thư mục hiện tại `.`.
- `--history-limit`: số message lịch sử lấy về ở mỗi lần poll từ `@sososo`. Mặc định: `20 message`.
- `--poll-interval`: thời gian chờ giữa các lần poll, tính theo giây. Mặc định: `2.0 giây`.
- `--max-polls-per-step`: số lần poll tối đa cho mỗi bước trước khi timeout. Mặc định: `90 lần poll`.

## Output

- Batch JSON: `batches/YYMMDD-HHMMSS/0001.json`
- Log file: `logs/sososo_logs/sososo-YYMMDD-HHMMSS-xxxxxx.log`

## Skill review title tieng Trung

Repo hien co them skill `review-sector-cybercrime-cn-titles` tai `skills/review-cn-sososo-search/review-sector-cybercrime-cn-titles`.

- Trigger: `$review-sector-cybercrime-cn-titles <folder>`
- Muc dich: review semantic cac title tieng Trung trong cac file `0001.json -> xxxx.json` va danh dau cac title lien quan toi cybercrime trong nhom `banking`, `securities`, `financial`, `government`
- Khong dung regex de quyet dinh `accept/reject`; phan danh gia do Codex suy luan
- Thu muc ket qua mac dinh: `skills/review-cn-sososo-search/reviews/review-cn-sososo-search/<ten-folder-dau-vao>`
- Thu muc log mac dinh: `skills/review-cn-sososo-search/logs/review-cn-sososo-search_logs/`

Artifacts chinh cua skill:

- `manifest.json`
- `normalized/*.input.json`
- `drafts/*.review.json`
- `reviewed/*.reviewed.json`
- `accepted_candidates.json`
- `rejected_candidates.json`
- `summary.json`

## Ghi chú

Script cần `telegram-mcp` đang chạy và Python environment có package `mcp`.
