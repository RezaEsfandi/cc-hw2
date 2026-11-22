# صف نوبت آزمایشگاه

برای اجرای تست‌های همراه تمرین از همین پوشه، روی لینوکس یا WSL:

```sh
python -m pip install -r requirements-dev.txt
pytest
```

## نسخهٔ فایل‌محور

یک فایل `.env` کنار `compose.yaml` بسازید و داخلش `APP_PORT=8182` بگذارید.
متغیر `baseUrl` کالکشن Postman روی همین پورت است. اگر پورت را تغییر دادید، مقدار
این متغیر را هم عوض کنید.

```sh
docker compose up -d --build --scale app=3
docker compose ps
curl http://localhost:8182/health
docker compose logs proxy
```

برای مرحلهٔ تک‌نسخه‌ای از `docker compose -f compose.single.yaml up -d --build`
استفاده کنید. داده در `queue-data` می‌ماند و با `docker compose down` پاک نمی‌شود.
دو چیدمان را همزمان با یک پورت بالا نیاورید.

روی یک صف خالی آزمایشی:

```sh
python tools/concurrent_join.py --url http://localhost:8182 --drain
python tools/concurrent_next.py --url http://localhost:8182
```

`concurrent_join.py` بعد از ارسال دستهٔ همزمان با `--drain` صف را هم می‌خواند
و خالی می‌کند. آزمایش دوم صف خالی را پر می‌کند و ۲۰۰ درخواست خروج می‌فرستد.

## نسخهٔ Redis و Prometheus

در شل لینوکس از پوشهٔ `part2`:

```sh
APP_PORT=8185 docker compose -p cc-hw2-redis -f compose.yaml -f compose.redis.yaml up -d --build --scale app=3
python tools/check_redis.py --url http://localhost:8185
python tools/concurrent_join.py --url http://localhost:8185 --drain
python tools/concurrent_next.py --url http://localhost:8185
```

در PowerShell مقدار `$env:APP_PORT = '8185'` را قبل از دستور Compose تنظیم کنید.
رابط Prometheus در `http://localhost:9192` است. Redis و exporter داخل شبکهٔ Compose
می‌مانند. طول صف با `max(queue_length{job="app"})` دیده می‌شود. هر سه نمونه
همان صف را اندازه می‌گیرند.

```promql
sum(rate(http_requests_total{job="app",route!="/metrics"}[1m]))
sum(rate(http_request_duration_seconds_sum{job="app",route!="/metrics"}[1m]))
  / sum(rate(http_request_duration_seconds_count{job="app",route!="/metrics"}[1m]))
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="app",route!="/metrics"}[1m])))
sum by (status) (rate(http_requests_total{job="app",status=~"4..|5.."}[1m]))
redis_up{job="db"}
redis_memory_used_bytes{job="db"}
redis_commands_processed_total{job="db"}
```

## انتشار

با push به `main`، پس از بررسی‌ها image به GHCR و فایل‌های `site/` به Pages می‌روند.
برای برگشت صفحه از تب Actions، گردش کار **Deploy a tagged Pages version** را انتخاب
کنید. شاخهٔ اجرای workflow روی `main` بماند و نام tag را به عنوان ورودی بدهید.
