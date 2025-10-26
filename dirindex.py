#!/usr/bin/env python3
r"""
dirindex - Directory Index Generator
2025-05-24

Generates an HTML index file listing files in a directory with proper HTML structure,
file metadata, and flexible sorting options. Supports glob patterns for file filtering,
recursive directory scanning, and multiple sorting methods including natural numeric sorting.

Examples:
    dirindex                                    # Index all files in current directory
    dirindex -i /path/to/files                  # Index specific directory
    dirindex -g "*.html" -g "*.css"             # Only HTML and CSS files (glob)
    dirindex -m "\.html$" -m "\.css$"           # Only HTML and CSS files (regex)
    dirindex -m "^data.*\.json$"                # Files starting with 'data' ending with .json
    dirindex -m "Report" --match-sensitive      # Case-sensitive regex match
    dirindex --sort-by-size-desc                # Largest files first
    dirindex -g "*.pdf" --sort-by-time          # Recent PDFs first
    dirindex -t "My Files" -o files.html        # Custom title and output name
    dirindex -r                                 # Recursively scan all subdirectories
    dirindex -r -maxdepth 2                     # Recursively scan up to 2 levels deep
"""

import argparse
import glob as glob_module
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

VERSION = "1.1.0"


def natural_sort_key(filename: str) -> list[str | int]:
    """
    Generate a sort key that handles numbers naturally.

    Args:
        filename: The filename to generate a sort key for

    Returns:
        A list of strings and integers for natural sorting
    """
    # Split filename into text and number parts
    parts = re.split(r'(\d+)', filename)
    # Convert numeric parts to integers for proper sorting
    return [int(part) if part.isdigit() else part for part in parts]


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted size string (e.g., "32KB", "1MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024}KB"
    else:
        return f"{size_bytes // (1024 * 1024)}MB"


def get_files_by_patterns(directory: Path, patterns: list[str], exclude_file: str,
                          recursive: bool = False, maxdepth: Optional[int] = None,
                          use_regex: bool = False, case_sensitive: bool = False) -> list[Path]:
    """
    Get files matching glob or regex patterns in directory, excluding the output file.

    Args:
        directory: Directory to scan for files
        patterns: List of glob or regex patterns to match
        exclude_file: Output filename to exclude from results
        recursive: Whether to recursively scan subdirectories
        maxdepth: Maximum recursion depth (1 = current directory only, 2 = one level deep, etc.)
        use_regex: Whether to use regex patterns instead of glob patterns
        case_sensitive: Whether regex matching should be case-sensitive (only used with use_regex=True)

    Returns:
        List of file paths matching any of the patterns
    """
    matched_files = set()

    # If no patterns specified, match all files
    if not patterns:
        patterns = ["*"] if not use_regex else [".*"]

    # Compile regex patterns if using regex mode
    compiled_patterns = []
    if use_regex:
        regex_flags = 0 if case_sensitive else re.IGNORECASE
        for pattern in patterns:
            try:
                compiled_patterns.append(re.compile(pattern, regex_flags))
            except re.error as e:
                print(f"Error: Invalid regex pattern '{pattern}': {e}", file=sys.stderr)
                sys.exit(1)

    def matches_pattern(filename: str) -> bool:
        """Check if filename matches any of the patterns."""
        if use_regex:
            return any(pattern.search(filename) for pattern in compiled_patterns)
        else:
            return any(glob_module.fnmatch.fnmatch(filename, pattern) for pattern in patterns)

    if recursive:
        # Recursive scanning with optional depth limit
        if maxdepth is not None:
            # Limited depth recursion - manually walk the directory tree
            def scan_directory(current_dir: Path, current_depth: int) -> None:
                if current_depth > maxdepth:
                    return

                # Scan files in current directory
                try:
                    for item in current_dir.iterdir():
                        if item.is_file():
                            # Check if file matches pattern
                            if matches_pattern(item.name):
                                if item.name != exclude_file:
                                    matched_files.add(item)
                        elif item.is_dir() and current_depth < maxdepth:
                            # Recurse into subdirectory if we haven't reached max depth
                            scan_directory(item, current_depth + 1)
                except PermissionError:
                    pass  # Skip directories we can't access

            scan_directory(directory, 1)
        else:
            # Unlimited depth recursion
            if use_regex:
                # For regex, manually walk all directories
                def scan_all_directories(current_dir: Path) -> None:
                    try:
                        for item in current_dir.iterdir():
                            if item.is_file():
                                if matches_pattern(item.name):
                                    if item.name != exclude_file:
                                        matched_files.add(item)
                            elif item.is_dir():
                                scan_all_directories(item)
                    except PermissionError:
                        pass  # Skip directories we can't access

                scan_all_directories(directory)
            else:
                # Unlimited depth recursion using ** glob pattern
                for pattern in patterns:
                    pattern_path = directory / "**" / pattern
                    for file_path in glob_module.glob(str(pattern_path), recursive=True):
                        file_obj = Path(file_path)
                        # Only include regular files, exclude directories and the output file
                        if file_obj.is_file() and file_obj.name != exclude_file:
                            matched_files.add(file_obj)
    else:
        # Non-recursive scanning
        if use_regex:
            # For regex, scan directory and match against patterns
            try:
                for item in directory.iterdir():
                    if item.is_file():
                        if matches_pattern(item.name):
                            if item.name != exclude_file:
                                matched_files.add(item)
            except PermissionError:
                pass  # Skip directories we can't access
        else:
            # Use glob to find matching files
            for pattern in patterns:
                pattern_path = directory / pattern
                for file_path in glob_module.glob(str(pattern_path)):
                    file_obj = Path(file_path)
                    # Only include regular files, exclude directories and the output file
                    if file_obj.is_file() and file_obj.name != exclude_file:
                        matched_files.add(file_obj)

    return list(matched_files)


def sort_files(files: list[Path], sort_method: str, directory: Path) -> list[Path]:
    """
    Sort files according to the specified method.

    Args:
        files: List of file paths to sort
        sort_method: Sorting method ('name', 'time', 'time-desc', 'size', 'size-desc')
        directory: Base directory for calculating relative paths (used for name sorting)

    Returns:
        Sorted list of file paths
    """
    if sort_method == "time":
        return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
    elif sort_method == "time-desc":
        return sorted(files, key=lambda f: f.stat().st_mtime, reverse=False)
    elif sort_method == "size":
        return sorted(files, key=lambda f: f.stat().st_size, reverse=True)
    elif sort_method == "size-desc":
        return sorted(files, key=lambda f: f.stat().st_size, reverse=False)
    else:  # Default to natural name sorting
        # Sort by full relative path for better organization in recursive mode
        def get_sort_key(f: Path) -> list[str | int]:
            try:
                rel_path = str(f.relative_to(directory))
            except ValueError:
                rel_path = f.name
            return natural_sort_key(rel_path)

        return sorted(files, key=get_sort_key)


def generate_html_content(directory: Path, output_file: str, page_title: str,
                         header_title: str, patterns: list[str], sort_method: str, columns: bool,
                         recursive: bool = False, maxdepth: Optional[int] = None,
                         use_regex: bool = False, case_sensitive: bool = False) -> str:
    """
    Generate the complete HTML content for the index file.

    Args:
        directory: Directory containing files
        output_file: Name of the output file to exclude
        page_title: Title for the HTML page
        header_title: Header text for the page
        patterns: List of glob or regex patterns for file matching
        sort_method: Method to sort files
        columns: Whether to use columnar layout
        recursive: Whether to recursively scan subdirectories
        maxdepth: Maximum recursion depth (only used with recursive=True)
        use_regex: Whether to use regex patterns instead of glob patterns
        case_sensitive: Whether regex matching should be case-sensitive

    Returns:
        Complete HTML content as string
    """
    matched_files = get_files_by_patterns(directory, patterns, output_file, recursive, maxdepth,
                                          use_regex, case_sensitive)
    sorted_files = sort_files(matched_files, sort_method, directory)
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Generate file entries
    if columns:
        # Columnar layout with table
        file_entries = ['        <table class="file-table">']
        file_entries.append('            <thead>')
        file_entries.append('                <tr>')
        file_entries.append('                    <th>Name</th>')
        file_entries.append('                    <th>Size</th>')
        file_entries.append('                    <th>Modified</th>')
        file_entries.append('                </tr>')
        file_entries.append('            </thead>')
        file_entries.append('            <tbody>')

        for file_path in sorted_files:
            stat = file_path.stat()
            size = format_file_size(stat.st_size)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%a %b %d %Y %H:%M:%S")

            # Calculate relative path from directory for display and linking
            try:
                rel_path = file_path.relative_to(directory)
            except ValueError:
                # Fallback if relative_to fails
                rel_path = file_path.name

            file_entries.append(f'''                <tr>
                    <td><a href="{rel_path}" class="file-link">{rel_path}</a></td>
                    <td class="size-col">{size}</td>
                    <td class="date-col">{mtime}</td>
                </tr>''')

        file_entries.append('            </tbody>')
        file_entries.append('        </table>')
        files_html = '\n'.join(file_entries)

        # Additional CSS for table layout
        table_css = '''
        .file-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .file-table th {
            background-color: #f8f9fa;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #dee2e6;
            font-weight: bold;
            color: #495057;
        }
        .file-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #dee2e6;
        }
        .file-table tr:hover {
            background-color: #f8f9fa;
        }
        .file-link {
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }
        .file-link:hover {
            text-decoration: underline;
        }
        .size-col {
            text-align: right;
            font-family: 'Courier New', monospace;
            color: #666;
        }
        .date-col {
            font-family: 'Courier New', monospace;
            color: #666;
            white-space: nowrap;
        }'''
    else:
        # Original flex layout
        file_entries = []
        for file_path in sorted_files:
            stat = file_path.stat()
            size = format_file_size(stat.st_size)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%a %b %d %Y %H:%M:%S")

            # Calculate relative path from directory for display and linking
            try:
                rel_path = file_path.relative_to(directory)
            except ValueError:
                # Fallback if relative_to fails
                rel_path = file_path.name

            file_entries.append(f'''        <a href="{rel_path}" class="file-item">
            <span class="file-name">{rel_path}</span>
            <span class="file-meta">{size} • {mtime}</span>
        </a>''')

        files_html = '\n'.join(file_entries)
        table_css = ''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        .file-count {{
            font-size: 0.6em;
            color: #666;
            font-weight: normal;
        }}
        .file-list {{
            margin-top: 30px;
        }}
        .file-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background-color: #f8f9fa;
            border-radius: 5px;
            text-decoration: none;
            color: #333;
            transition: background-color 0.2s;
        }}
        .file-item:hover {{
            background-color: #e9ecef;
        }}
        .file-name {{
            font-weight: bold;
            color: #3498db;
        }}
        .file-meta {{
            font-size: 0.9em;
            color: #666;
        }}
        .timestamp {{
            text-align: center;
            color: #999;
            font-size: 0.8em;
            margin-top: 30px;
        }}{table_css}
    </style>
</head>
<body>
    <h1>
        <span>{header_title}</span>
        <span class="file-count">{len(sorted_files)} files</span>
    </h1>
    <div class="file-list">
{files_html}
    </div>
    <div class="timestamp">
        Generated on {current_time}
    </div>
</body>
</html>'''


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Generate an HTML index file listing files in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Index all files in current directory
  %(prog)s -i /path/to/files                 # Index specific directory
  %(prog)s -g "*.html" -g "*.css"            # Only HTML and CSS files (glob)
  %(prog)s -m "\.html$" -m "\.css$"          # Only HTML and CSS files (regex)
  %(prog)s -m "^data.*\.json$"               # Files starting with 'data' ending with .json
  %(prog)s -m "Report" --match-sensitive     # Case-sensitive regex match
  %(prog)s --sort-by-size-desc               # Largest files first
  %(prog)s -g "*.pdf" --sort-by-time         # Recent PDFs first
  %(prog)s -t "My Files" -o files.html       # Custom title and output name
  %(prog)s -c --sort-by-size                 # Columnar layout, sorted by size
  %(prog)s -r                                 # Recursively scan all subdirectories
  %(prog)s -r -maxdepth 2                     # Recursively scan up to 2 levels deep
  %(prog)s -r -maxdepth 3 -g "*.jpg"          # Recursively find JPG files, 3 levels deep
  %(prog)s -r -m "\\.py$"                     # Recursively find Python files (regex)
        """
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=str,
        default=".",
        help="Input directory to scan for files (default: current directory)"
    )
    parser.add_argument(
        "-t", "--title",
        type=str,
        default="Directory Index",
        help="Set the page title (default: 'Directory Index')"
    )
    parser.add_argument(
        "-H", "--header",
        type=str,
        help="Set the header text (default: 'Files in [directory name]')"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="index.html",
        help="Set output filename (default: 'index.html')"
    )
    # Pattern matching options - mutually exclusive
    pattern_group = parser.add_mutually_exclusive_group()
    pattern_group.add_argument(
        "-g", "--glob",
        action="append",
        dest="patterns",
        help="Glob pattern to match files (can be used multiple times). Default: all files"
    )
    pattern_group.add_argument(
        "-m", "--regex",
        action="append",
        dest="regex_patterns",
        help="Regex pattern to match files (can be used multiple times). Mutually exclusive with -g"
    )
    parser.add_argument(
        "--match-sensitive",
        action="store_true",
        help="Make regex matching case-sensitive (only used with -m/--regex)"
    )
    parser.add_argument(
        "-c", "--columns",
        action="store_true",
        help="Use columnar layout with proper alignment for name, size, and date"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan subdirectories"
    )
    parser.add_argument(
        "-maxdepth",
        type=int,
        metavar="DEPTH",
        help="Limit recursion depth (only valid with -r). 1 = current directory only, 2 = one level deep, etc."
    )

    # Sorting options
    sort_group = parser.add_mutually_exclusive_group()
    sort_group.add_argument(
        "--sort-by-time",
        action="store_const",
        const="time",
        dest="sort_method",
        help="Sort by modification time, newest first"
    )
    sort_group.add_argument(
        "--sort-by-time-desc",
        action="store_const",
        const="time-desc",
        dest="sort_method",
        help="Sort by modification time, oldest first"
    )
    sort_group.add_argument(
        "--sort-by-size",
        action="store_const",
        const="size",
        dest="sort_method",
        help="Sort by file size, largest first"
    )
    sort_group.add_argument(
        "--sort-by-size-desc",
        action="store_const",
        const="size-desc",
        dest="sort_method",
        help="Sort by file size, smallest first"
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s v{VERSION}\nhttps://github.com/jftuga/dirindex",
        help="Show version number and exit"
    )

    # Set default sort method
    parser.set_defaults(sort_method="name")

    return parser


def main() -> None:
    """Main function to generate directory index file."""
    parser = create_argument_parser()

    # Show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Validate -maxdepth requires -r
    if args.maxdepth is not None and not args.recursive:
        parser.error("-maxdepth can only be used with -r/--recursive")

    # Validate --match-sensitive requires -m
    if args.match_sensitive and not args.regex_patterns:
        parser.error("--match-sensitive can only be used with -m/--regex")

    # Convert input directory to Path object
    input_dir = Path(args.input_dir).resolve()

    # Validate input directory
    if not input_dir.is_dir():
        print(f"Error: Directory '{input_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Set default header if not provided
    header_title = args.header or f"Files in {input_dir.name}"

    # Handle glob patterns and regex patterns
    use_regex = bool(args.regex_patterns)
    patterns = args.regex_patterns if use_regex else (args.patterns or [])
    case_sensitive = args.match_sensitive

    print(f"Scanning directory: {input_dir}")
    if patterns:
        pattern_type = "regex" if use_regex else "glob"
        case_info = " (case-sensitive)" if (use_regex and case_sensitive) else " (case-insensitive)" if use_regex else ""
        print(f"Using {pattern_type} patterns{case_info}: {', '.join(patterns)}")
    else:
        print("Scanning all files")
    print(f"Sort method: {args.sort_method}")

    # Check if any files exist matching the patterns
    matched_files = get_files_by_patterns(input_dir, patterns, args.output, args.recursive, args.maxdepth,
                                          use_regex, case_sensitive)

    if not matched_files:
        if patterns:
            print(f"Error: No files found matching patterns {patterns} in directory '{input_dir}'.", file=sys.stderr)
        else:
            print(f"Error: No files found in directory '{input_dir}'.", file=sys.stderr)
        print("Index file not created.", file=sys.stderr)
        sys.exit(1)

    # Generate output path
    output_path = input_dir / args.output

    print(f"Generating HTML index file: {output_path}")

    # Generate and write HTML content
    html_content = generate_html_content(
        input_dir, args.output, args.title, header_title, patterns, args.sort_method, args.columns,
        args.recursive, args.maxdepth, use_regex, case_sensitive
    )

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except OSError as e:
        print(f"Error writing file '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)

    print("Index file created successfully!")
    print(f"Found {len(matched_files)} files:")

    # Show first few files as preview
    sorted_files = sort_files(matched_files, args.sort_method, input_dir)
    for i, file_path in enumerate(sorted_files[:5]):
        try:
            rel_path = file_path.relative_to(input_dir)
            print(f"  - {rel_path}")
        except ValueError:
            print(f"  - {file_path.name}")

    if len(sorted_files) > 5:
        print(f"  ... and {len(sorted_files) - 5} more")


if __name__ == "__main__":
    main()
