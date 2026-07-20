#!/usr/bin/env python3
"""
LeakyRAG CTF — Server
"可搜索加密"的向量数据库，实际上分数泄漏导致向量可被完全重建。
"""
import json
import os
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np

DIM = 64
FLAG = os.environ.get("FLAG", "flag{l34ky_v3ct0r_s34rch_1s_n0t_3ncrypt10n}")

# ============================================================
# "可搜索加密" Embedding — 公开且确定性
# 比值编码：前 63 维编码字符，第 64 维为参考。
# v[i] / v[63] = exp((char_i - 128) / 64)
# 归一化不改变比值 → 重建向量后本地解码即得 flag。
# ============================================================
def embed(text: str) -> np.ndarray:
    data = text.encode()
    v = np.ones(DIM, dtype=np.float64)
    n = min(len(data), DIM - 1)
    for i in range(n):
        ratio = np.exp((data[i] - 128) / 64.0)
        v[i] = ratio
    return v / np.linalg.norm(v)


def decode(v_norm: np.ndarray) -> str:
    """从归一化向量恢复文本"""
    v = np.array(v_norm, dtype=np.float64)
    v = v / np.linalg.norm(v)
    ref = v[-1]
    chars = []
    for i in range(DIM - 1):
        ratio = v[i] / ref
        char_code = int(round(np.log(ratio) * 64 + 128))
        if 32 <= char_code <= 126:
            chars.append(chr(char_code))
        else:
            break
    return ''.join(chars)


# ============================================================
# 文档库
# ============================================================
def init_docs():
    docs = {}
    # 普通文档
    samples = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is revolutionizing the world",
        "Python is a popular programming language",
        "The capital of France is Paris",
        "Quantum computing uses qubits instead of bits",
        "Blockchain is a decentralized ledger technology",
        "Neural networks are inspired by biological neurons",
        "The Earth orbits around the Sun",
        "Encryption is the process of encoding information",
        "Docker containers provide isolated environments",
    ]
    for i, text in enumerate(samples):
        doc_id = f"doc_{i:03d}"
        docs[doc_id] = {
            "text": text,
            "vector": embed(text),
            "protected": False,
        }

    # Flag 文档
    docs["flag_doc"] = {
        "text": FLAG,
        "vector": embed(FLAG),
        "protected": True,
    }

    # 加一些干扰文档
    noise_texts = [
        f"Noise document number {i}: {secrets.token_hex(16)}"
        for i in range(50)
    ]
    for i, text in enumerate(noise_texts):
        doc_id = f"noise_{i:03d}"
        docs[doc_id] = {
            "text": text,
            "vector": embed(text),
            "protected": False,
        }

    return docs


docs = init_docs()


# ============================================================
# HTTP Handler
# ============================================================
class Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filename: str, content_type: str):
        try:
            with open(filename, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._json({"error": "Not found"}, 404)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.rstrip("/")

        # Serve HTML pages
        html_pages = {"": "index.html", "/index.html": "index.html",
                     "/search.html": "search.html", "/upload.html": "upload.html",
                     "/docs.html": "docs.html"}
        if path in html_pages:
            self._serve_file(html_pages[path], "text/html")
            return

        if path.startswith("/api/doc/"):
            doc_id = path.split("/api/doc/")[1]
            if doc_id in docs:
                doc = docs[doc_id]
                if doc["protected"]:
                    self._json({"error": "This document is protected by SecureAI encryption"}, 403)
                else:
                    self._json({
                        "doc_id": doc_id,
                        "text": doc["text"],
                        "vector": None,  # "加密保护"
                    })
            else:
                self._json({"error": "Document not found"}, 404)
        elif path == "/api/stats":
            self._json({"total_docs": len(docs), "dim": DIM})
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.rstrip("/")
        body = self._read_body()

        if path == "/api/search":
            vec = np.array(body.get("vector", []), dtype=np.float64)
            top_k = min(body.get("top_k", 5), 20)

            if vec.shape != (DIM,):
                self._json({"error": f"Vector must be {DIM}-dimensional"}, 400)
                return

            # 归一化
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            # 计算余弦相似度
            results = []
            for doc_id, doc in docs.items():
                score = float(np.dot(vec, doc["vector"]))
                if doc["protected"]:
                    snippet = "[PROTECTED by SecureAI]"
                else:
                    snippet = doc["text"][:60]
                results.append({
                    "doc_id": doc_id,
                    "score": score,
                    "snippet": snippet,
                })

            results.sort(key=lambda x: -x["score"])
            self._json({"results": results[:top_k]})

        elif path == "/api/upload":
            text = body.get("text", "").strip()
            if not text or len(text) > 10000:
                self._json({"error": "Invalid text"}, 400)
                return

            doc_id = f"user_{secrets.token_hex(8)}"
            docs[doc_id] = {
                "text": text,
                "vector": embed(text),
                "protected": False,
            }
            self._json({"doc_id": doc_id, "message": "Document uploaded and indexed"})

        else:
            self._json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        pass  # 安静模式


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"SecureRAG running on port {port}")
    server.serve_forever()
