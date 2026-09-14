# -*- coding: utf-8 -*-
"""用 backend/.venv 跑 T-008 相关测试"""
import subprocess
import sys

PY = r'E:\Code\AideanBot\backend\.venv\Scripts\python.exe'
r = subprocess.run([PY, '-m', 'pytest', '-q', '--no-header', '--maxfail=2',
                    'tests/test_langbot.py::test_ingest_url_other_users_space_maps_30004',
                    'tests/test_langbot.py::test_doc_status_other_users_space_maps_30004',
                    'tests/test_langbot.py::test_ingest_owner_unaffected_status_and_doc_flow',
                    'tests/test_langbot.py::test_ingest_endpoint_url_over_512_maps_10005',
                    'tests/test_langbot.py::test_ingest_endpoint_url_empty_maps_10005',
                    'tests/test_langbot.py::test_ingest_endpoint_passes_user_id_to_service'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   cwd=r'E:\Code\AideanBot\backend', timeout=300)
print('rc=', r.returncode)
out = (r.stdout + r.stderr)
print(out[-2500:])
