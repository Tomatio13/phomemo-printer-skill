from __future__ import annotations

import argparse

from ..mcp.layout_server import run_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phomemo MCPサーバーを起動")
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio", "http", "streamable-http"],
        default="sse",
        help="MCPトランスポート種別 (default: sse)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="ホスト (sse/http時のみ)")
    parser.add_argument("--port", type=int, default=8000, help="ポート (sse/http時のみ)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_server(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
