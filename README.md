# CTI-Collect-Feeds

`sososo.py` la script crawl ket qua tu bot Telegram `@sososo`, chi trich xuat `title + link` va ghi ket qua thanh cac file JSON theo batch.

## Tinh nang hien co

- Gui query toi `@sososo` qua `telegram-mcp`
- Crawl theo tung trang voi `--max-page`
- Tach va dedupe `title + link`
- Ghi ket qua JSON theo batch voi `--batch`
- Luu file vao `batches/YYMMDD-HHMMSS/0001.json`
- Phat hien challenge cua bot theo kien truc detector mo rong
- Ho tro challenge phep tinh co goi y dap an
- Hoi user xac nhan `y/n` sau khi giai challenge de tiep tuc crawl
- Console log mau theo tung buoc va luu file log vao `logs/sososo_logs`
- Ket thuc chuong trinh chi in summary ra console, khong dump toan bo items

## Cach dung

```powershell
python sososo.py --query "bank fake" --max-page 10 --batch 30
```

## Tham so chinh

- `--query`: tu khoa can crawl
- `--max-page`: so trang toi da se crawl
- `--batch`: so item trong moi file JSON
- `--output-dir`: thu muc goc de ghi `batches/` va `logs/`
- `--history-limit`: so message lich su moi lan poll
- `--poll-interval`: thoi gian cho giua cac lan poll
- `--max-polls-per-step`: so lan poll toi da cho moi buoc

## Output

- Batch JSON: `batches/YYMMDD-HHMMSS/0001.json`
- Log file: `logs/sososo_logs/sososo-YYMMDD-HHMMSS-xxxxxx.log`

## Ghi chu

Script can `telegram-mcp` dang chay va Python environment co package `mcp`.
