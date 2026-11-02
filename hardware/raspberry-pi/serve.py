#!/usr/bin/env python3
"""Serve the Just In Case library to every device on the Pi's hotspot.

Standard library only. Requests for other host names (phones checking for
internet, or any site someone types) are redirected to the library, so phones
show it as a captive portal sign-in page.

    sudo python3 serve.py                      # port 80, serves ../../dist/site
    python3 serve.py --port 8080 --dir /path/to/site
"""

import argparse
import ipaddress
import mimetypes
import os
import socket
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
mimetypes.add_type("application/manifest+json", ".webmanifest")
DEFAULT_SITE = HERE.parent.parent / "dist" / "site"


class LibraryHandler(SimpleHTTPRequestHandler):
    portal = "10.42.0.1"
    own_names = set()

    def is_for_us(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if not host or host in self.own_names:
            return True
        try:
            ipaddress.ip_address(host)
            return True  # Any direct IP address, for example from the home network.
        except ValueError:
            return False

    def send_head(self):
        if not self.is_for_us():
            self.send_response(302)
            self.send_header("Location", "http://%s/" % self.portal)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        # Clean URLs: /purify-water opens /purify-water.html
        path = self.translate_path(self.path)
        if not os.path.exists(path) and os.path.exists(path + ".html"):
            self.path = self.path.split("?", 1)[0] + ".html"
        elif not os.path.exists(path) and not self.path.startswith("/index"):
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "max-age=3600")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # Quiet: the Pi may run from a read-only card for months.


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(DEFAULT_SITE), help="folder with the built site (default: %(default)s)")
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--portal", default="10.42.0.1", help="address phones are redirected to (the hotspot IP)")
    args = ap.parse_args()

    site = Path(args.dir)
    if not (site / "index.html").exists():
        raise SystemExit("No library at %s. Run: python3 tools/build.py" % site)

    hostname = socket.gethostname().lower()
    LibraryHandler.portal = args.portal
    LibraryHandler.own_names = {"localhost", hostname, hostname + ".local", args.portal}
    handler = partial(LibraryHandler, directory=str(site))
    server = ThreadingHTTPServer(("", args.port), handler)
    print("Serving %s on port %d. Hotspot users: http://%s/" % (site, args.port, args.portal))
    server.serve_forever()


if __name__ == "__main__":
    main()
