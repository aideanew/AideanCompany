# AB-P004 T-021 资产复用表（同一 URL 两次入库）

- DB 直查 p0-cache-001 hit_count：0（无该探针行）
- 微信抓取请求数（代码口径）：首次入库=1（真实直抓）；第二次入库=0（命中 READY 资产，直接 content_markdown 重传引擎）
- 证据：kb.py ingest_url 先查后抓 + test_p0_asset_cache.py resolver.fetch_count 断言（第二次=1 即 0 增量）