"""Minimal accessible WSGI shell for local demos and smoke deployment checks."""

from __future__ import annotations

import json
from html import escape
from typing import Callable

from .api import CampusAIApplication


INDEX_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CampusAI</title><style>body{font:16px system-ui;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#172033}main{display:grid;gap:1rem}textarea{width:100%;min-height:7rem;padding:.7rem}button{padding:.7rem 1rem;cursor:pointer}.answer{white-space:pre-wrap;background:#f3f6fa;padding:1rem;border-radius:.5rem}.status{min-height:1.5rem}</style></head>
<body><header><h1>CampusAI</h1><p>Trợ lý tri thức đại học có dẫn nguồn.</p></header><main>
<form id="query-form"><label for="question">Câu hỏi</label><textarea id="question" name="question" required aria-describedby="hint"></textarea><small id="hint">Chỉ nhận câu trả lời có bằng chứng trong tài liệu đã lập chỉ mục.</small><button type="submit">Hỏi</button></form>
<p id="status" class="status" role="status" aria-live="polite"></p><section aria-labelledby="answer-title"><h2 id="answer-title">Trả lời</h2><div id="answer" class="answer">Chưa có câu trả lời.</div></section></main>
<script>const f=document.querySelector('#query-form'),s=document.querySelector('#status'),a=document.querySelector('#answer');f.addEventListener('submit',async e=>{e.preventDefault();s.textContent='Đang tìm bằng chứng…';a.textContent='';try{const r=await fetch('/api/query',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:new FormData(f).get('question')})});const d=await r.json();if(!r.ok||!d.ok)throw Error(d.error_code||'query_failed');a.textContent=d.answer.answer;const c=d.answer.citations||[];if(c.length)a.textContent+='\\n\\nNguồn: '+c.map(x=>`trang ${x.page}`).join(', ');s.textContent=d.answer.abstained?'Chưa đủ bằng chứng.':'Hoàn tất.'}catch(err){s.textContent='Có lỗi: '+err.message}});</script></body></html>"""


def make_wsgi_app(application: CampusAIApplication) -> Callable:
    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        if path == "/" and method == "GET":
            body = INDEX_HTML.encode("utf-8")
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
            return [body]
        if path in {"/health", "/ready", "/metrics"} and method == "GET":
            value = {"/health": application.health, "/ready": application.readiness, "/metrics": application.metrics_snapshot}[path]()
            return _json_response(value, start_response)
        if path == "/api/query" and method == "POST":
            try:
                length = min(int(environ.get("CONTENT_LENGTH") or 0), 64_000)
                payload = json.loads(environ["wsgi.input"].read(length))
                value = application.query(payload.get("question", ""))
                return _json_response(value, start_response, 200 if value.get("ok") else 400)
            except (ValueError, json.JSONDecodeError):
                return _json_response({"ok": False, "error_code": "invalid_json"}, start_response, 400)
        return _json_response({"ok": False, "error_code": "not_found"}, start_response, 404)
    return app


def _json_response(value, start_response, status: int = 200):
    body = json.dumps(value, ensure_ascii=False).encode("utf-8")
    start_response(f"{status} {'OK' if status == 200 else 'Error'}", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]
