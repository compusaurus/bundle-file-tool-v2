"""Launch the local BFT browser workspace."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser

from web.server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bft-web",
        description="Start the loopback-only Bundle File Tool web workspace.",
    )
    parser.add_argument("--port", type=int, default=0,
                        help="loopback port (default: choose an available port)")
    parser.add_argument("--no-browser", action="store_true",
                        help="print the private URL without opening a browser")
    parser.add_argument("--browser-picker", action="store_true",
                        help="choose server files in the browser without native desktop dialogs")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.browser_picker:
        os.environ["BFT_WEB_BROWSER_PICKER"] = "1"
    server = create_server(port=args.port)
    print(server.session_url, flush=True)
    if not args.no_browser:
        threading.Timer(0.25, webbrowser.open,
                        args=(server.session_url,)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
