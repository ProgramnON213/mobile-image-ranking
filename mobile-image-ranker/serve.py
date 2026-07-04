#!/usr/bin/env python3
import http.server
import socket
import socketserver
import os
import sys

PORT_DEFAULT = 8000

def get_local_ips():
    """Retrieves all local IPv4 addresses on this machine."""
    ip_list = []
    # Method 1: Connect socket to find default interface IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        default_ip = s.getsockname()[0]
        ip_list.append(default_ip)
        s.close()
    except Exception:
        pass

    # Method 2: Get all interface IPs (fallback/alternatives)
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip not in ip_list and not ip.startswith("127."):
                ip_list.append(ip)
    except Exception:
        pass
        
    return ip_list

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler that adds caching headers and handles CORS."""
    def end_headers(self):
        # Allow cross-origin resource sharing (CORS) for development convenience
        self.send_header('Access-Control-Allow-Origin', '*')
        # Prevent aggressive caching of app scripts during development/updates
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def start_server(port=PORT_DEFAULT):
    # Change working directory to this file's folder to serve correct files
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    local_ips = get_local_ips()
    
    print("=" * 65)
    print(" 📂 MOBILE IMAGE RANKER SERVER IS READY!")
    print("=" * 65)
    print("\n1. Make sure your Phone and PC are connected to the SAME Wi-Fi.")
    print("2. Open one of the following links in your phone's browser:\n")
    
    for ip in local_ips:
        print(f"    👉  http://{ip}:{port}/index.html")
    
    print(f"\n   (On your PC, you can view it at: http://localhost:{port}/index.html)")
    print("\n3. If you want to install it as an App on your phone:")
    print("   - On Android: Tap Chrome settings (3 dots) -> 'Install App' or 'Add to Home Screen'")
    print("   - On iOS (Safari): Tap the Share button -> 'Add to Home Screen'")
    print("-" * 65)
    print("Press Ctrl+C to stop the server at any time.\n")

    # SocketServer configuration
    # Bind to '' (0.0.0.0) so it's accessible across the network
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError launching server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mobile Image Ranker Server")
    parser.add_argument("--port", "-p", type=int, default=PORT_DEFAULT, help="Port to serve the app on (default: 8000)")
    args = parser.parse_args()
    start_server(args.port)
