#!/usr/bin/env python3
"""离线 EaglercraftX 一体化服务：
- 静态托管 /workspace/web（提供单文件客户端）
- 把到该端口的 WebSocket 升级请求透明转发到本机游戏端口(默认 25565)

这样浏览器只需通过 Trae 已能连通的单个 localhost 端口(默认 8081)，
即可同时加载网页和连接游戏服务器，无需暴露额外端口。
使用: python3 web_ws_proxy.py [host] [port] [game_port]
"""
import os, sys, socket, threading

WEB_DIR = "/workspace/web"
GAME_HOST = "127.0.0.1"
GAME_PORT = 25565

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".ico": "image/x-icon",
}

def _recv_head(sock):
    """读 HTTP 请求头直到 \\r\\n\\r\\n，返回 (head_bytes, leftover_bytes)。"""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > 65536:
            break
    if b"\r\n\r\n" in data:
        head, _, rest = data.partition(b"\r\n\r\n")
        return head + b"\r\n\r\n", rest
    return data, b""

def _serve_static(conn, path):
    if path in ("/", ""):
        path = "/index.html"
    p = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
    if not p.startswith(os.path.abspath(WEB_DIR) + os.sep) and not p == os.path.abspath(WEB_DIR):
        p = os.path.join(WEB_DIR, "index.html")  # 越界回退首页
    if os.path.isdir(p):
        p = os.path.join(p, "index.html")
    if not os.path.isfile(p):
        body = b"404 Not Found"
        conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: %d\r\nConnection: close\r\nContent-Type: text/plain\r\n\r\n" % len(body) + body)
        return
    ext = os.path.splitext(p)[1].lower()
    ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
    with open(p, "rb") as f:
        body = f.read()
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nContent-Type: %s\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n" % (len(body), ctype.encode()) + body)

def _relay_once(src, dst):
    try:
        data = src.recv(65536)
        if not data:
            return False
        dst.sendall(data)
    except Exception:
        return False
    return True

def _ws_proxy(conn, head, leftover):
    """把本端口的 WebSocket 请求透明转发到 GAME_HOST:GAME_PORT，随后双向转发字节。"""
    game = None
    try:
        game = socket.create_connection((GAME_HOST, GAME_PORT), timeout=10)
    except Exception as e:
        try:
            conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        except Exception:
            pass
        return
    try:
        # 把客户端发来的原始升级请求(含 Host/Sec-WebSocket-Key)完整转发给游戏服务器
        game.sendall(head + leftover)
    except Exception:
        game.close()
        conn.close()
        return
    # 双向转发
    t = threading.Thread(target=lambda: (lambda a, b: None)(None, None))  # placeholder
    def pipe(a, b):
        try:
            while True:
                if not _relay_once(a, b):
                    break
        except Exception:
            pass
        finally:
            try: b.shutdown(socket.SHUT_WR)
            except Exception: pass
    threading.Thread(target=pipe, args=(game, conn), daemon=True).start()
    pipe(conn, game)
    try: game.close()
    except Exception: pass
    try: conn.close()
    except Exception: pass

def handle(conn):
    try:
        head, leftover = _recv_head(conn)
        head_lower = head.lower()
        first_line = head.split(b"\r\n", 1)[0].decode("latin-1", "replace") if head else ""
        parts = first_line.split(" ")
        method = parts[0] if len(parts) > 0 else ""
        target = parts[1] if len(parts) > 1 else "/"
        if method in ("GET", "POST", "HEAD") and b"upgrade: websocket" in head_lower:
            _ws_proxy(conn, head, leftover)
            return
        _serve_static(conn, target)
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8081
    gport = int(sys.argv[3]) if len(sys.argv) > 3 else GAME_PORT
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(128)
    print(f"[proxy] web+ws on {host}:{port} -> game ws {GAME_HOST}:{gport}", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()