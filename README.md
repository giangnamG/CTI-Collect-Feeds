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

## Skill review title tiếng Trung

Repo hiện có skill `review-sector-cybercrime-cn-titles` tại `skills/review-sector-cybercrime-cn-titles`.

- Trigger: `$review-sector-cybercrime-cn-titles <batch-token|folder-path>`
- `batch-token|folder-path` là tên thư mục hoặc đường dẫn tới thư mục chứa kết quả batch JSON do `sososo.py` tạo ra sau khi crawl xong, ví dụ `batches/260318-233535/`
- Nếu truyền bare token như `260318-233535`, skill sẽ tự resolve sang `batches/<token>`
- Mục đích: review semantic các title tiếng Trung trong các file `0001.json -> xxxx.json` và đánh dấu các title liên quan tới cybercrime trong nhóm `banking`, `securities`, `financial`, `government`
- Không dùng regex để quyết định `accept/reject`; phần đánh giá do Codex suy luận theo ngữ nghĩa
- Thư mục kết quả mặc định: `reviews/review-cn-sososo-search/<tên-folder-đầu-vào>`
- Thư mục log mặc định: `logs/review-cn-sososo-search_logs/`
- Workspace root mặc định là thư mục đang làm việc hoặc thư mục cha gần nhất có `batches/`; có thể override bằng env var `REVIEW_SECTOR_CYBERCRIME_CN_ROOT`

Workflow ngắn:

```powershell
python skills/review-sector-cybercrime-cn-titles/scripts/prepare_review_folder.py --input-dir "260318-233535"
python skills/review-sector-cybercrime-cn-titles/scripts/show_normalized_batch.py --manifest "reviews/review-cn-sososo-search/260318-233535/manifest.json" --list-files
python skills/review-sector-cybercrime-cn-titles/scripts/show_normalized_batch.py --manifest "reviews/review-cn-sososo-search/260318-233535/manifest.json" --source-file "0001.json"
python skills/review-sector-cybercrime-cn-titles/scripts/persist_review_folder.py --manifest "reviews/review-cn-sososo-search/260318-233535/manifest.json"
```

Giải thích workflow:

- `prepare_review_folder.py`: quét thư mục input, chỉ lấy các file JSON được đánh số như `0001.json`, normalize dữ liệu đầu vào, tạo `manifest.json`, và dựng sẵn các thư mục làm việc như `normalized/`, `drafts/`, `reviewed/`.
- `show_normalized_batch.py --list-files`: đọc `manifest.json` và liệt kê những file nguồn nào đã được chuẩn hóa, mỗi file có bao nhiêu item, giúp biết chính xác batch nào cần review.
- `show_normalized_batch.py --source-file "0001.json"`: mở một normalized batch cụ thể để reviewer xem đúng dữ liệu đã được chuẩn hóa trước khi đưa ra quyết định semantic.
- Bước review semantic: Codex hoặc reviewer phải tạo `drafts/<file>.review.json` cho từng file, giữ nguyên `title`, `link`, `source_file`, `item_index`, rồi bổ sung `title_vi`, `decision`, `reason`, `sector_tags`, `crime_signals`, `priority`.
- `title_vi` và `reason` phải viết bằng tiếng Việt.
- Các title dạng tin tức, bản tin, thông báo, báo cáo sự cố, hoặc chỉ mang tính đưa tin phải `reject`; chỉ ưu tiên các title thể hiện mua/bán/trao đổi/môi giới/giao dịch trung gian/hack hoặc hoạt động cybercrime có tính vận hành.
- `persist_review_folder.py`: validate toàn bộ draft review, khóa contract đầu ra, rồi tổng hợp sang `reviewed/`, `accepted_candidates.json`, `rejected_candidates.json`, `summary.json`.
- `run_regression.py`: chỉ dùng khi sửa script của skill; script này kiểm tra end-to-end flow `prepare -> inspect -> persist` để tránh làm hỏng workflow review hiện có.
- Khi gọi trực tiếp bằng skill `$review-sector-cybercrime-cn-titles`, Codex sẽ tự chạy toàn bộ flow này nếu input hợp lệ, nên người dùng thường không cần tự gõ từng lệnh tay.

Artifacts chính của skill:

- `manifest.json`
- `normalized/*.input.json`
- `drafts/*.review.json`
- `reviewed/*.reviewed.json`
- `accepted_candidates.json`
- `rejected_candidates.json`
- `summary.json`

## Ghi chú

Script cần `telegram-mcp` đang chạy và Python environment có package `mcp`.



