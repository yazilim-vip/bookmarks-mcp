from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bookmarks-mcp",
        description="MCP server + local web UI for personal bookmarks",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("mcp", help="Run the stdio MCP server (default when no command is given)")

    imp = sub.add_parser("import", help="Import bookmarks from a file")
    imp.add_argument("file", help="Path to the file to import")
    imp.add_argument("--format", choices=["html", "json"], default="html")

    exp = sub.add_parser("export", help="Export bookmarks to a file")
    exp.add_argument("file", help="Path to the file to write")
    exp.add_argument("--format", choices=["html", "json"], default="html")

    sub.add_parser("info", help="Print storage location and library stats")

    args = parser.parse_args()
    command = args.command or "mcp"

    if command == "mcp":
        from bookmarks_mcp.server import run_mcp

        run_mcp()
    elif command == "import":
        from bookmarks_mcp.importers import run_import

        run_import(args.file, args.format)
    elif command == "export":
        from bookmarks_mcp.importers import run_export

        run_export(args.file, args.format)
    elif command == "info":
        from bookmarks_mcp.info import print_info

        print_info()
    else:
        parser.print_help()
        sys.exit(1)
