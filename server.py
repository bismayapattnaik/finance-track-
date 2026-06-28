import http.server
import socketserver
import socket
import os

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

PORT = 8000
_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_DIR)

Handler = http.server.SimpleHTTPRequestHandler
# Add no-cache headers so it always live-tracks updates
class NoCacheHandler(Handler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
    ip = get_local_ip()
    print("="*50)
    print("DASHBOARD SERVER RUNNING!")
    print(f"To view on your phone (on same WiFi), open:")
    print(f"http://{ip}:{PORT}/dashboard.html")
    print("="*50)
    httpd.serve_forever()
