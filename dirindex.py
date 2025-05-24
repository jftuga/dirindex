#!/usr/bin/env python3
r"""
dirindex - Directory Index Generator
2025-05-24

Generates an HTML index file listing files in a directory with proper HTML structure,
file metadata, and flexible sorting options. Supports glob patterns for file filtering
and multiple sorting methods including natural numeric sorting.

Examples:
    dirindex                                    # Index all files in current directory
    dirindex -i /path/to/files                 # Index specific directory
    dirindex -g "*.html" -g "*.css"            # Only HTML and CSS files
    dirindex --sort-by-size-desc               # Largest files first
    dirindex -g "*.pdf" --sort-by-time         # Recent PDFs first
    dirindex -t "My Files" -o files.html       # Custom title and output name
"""

import argparse
import glob as glob_module
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

VERSION = "1.0.0"


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


def get_files_by_patterns(directory: Path, patterns: list[str], exclude_file: str) -> list[Path]:
    """
    Get files matching glob patterns in directory, excluding the output file.
    
    Args:
        directory: Directory to scan for files
        patterns: List of glob patterns to match
        exclude_file: Output filename to exclude from results
        
    Returns:
        List of file paths matching any of the patterns
    """
    matched_files = set()
    
    # If no patterns specified, match all files
    if not patterns:
        patterns = ["*"]
    
    for pattern in patterns:
        # Use glob to find matching files
        pattern_path = directory / pattern
        for file_path in glob_module.glob(str(pattern_path)):
            file_obj = Path(file_path)
            # Only include regular files, exclude directories and the output file
            if file_obj.is_file() and file_obj.name != exclude_file:
                matched_files.add(file_obj)
    
    return list(matched_files)


def sort_files(files: list[Path], sort_method: str) -> list[Path]:
    """
    Sort files according to the specified method.
    
    Args:
        files: List of file paths to sort
        sort_method: Sorting method ('name', 'time', 'time-desc', 'size', 'size-desc')
        
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
        return sorted(files, key=lambda f: natural_sort_key(f.name))


def generate_html_content(directory: Path, output_file: str, page_title: str, 
                         header_title: str, patterns: list[str], sort_method: str, columns: bool) -> str:
    """
    Generate the complete HTML content for the index file.
    
    Args:
        directory: Directory containing files
        output_file: Name of the output file to exclude
        page_title: Title for the HTML page
        header_title: Header text for the page
        patterns: List of glob patterns for file matching
        sort_method: Method to sort files
        columns: Whether to use columnar layout
        
    Returns:
        Complete HTML content as string
    """
    matched_files = get_files_by_patterns(directory, patterns, output_file)
    sorted_files = sort_files(matched_files, sort_method)
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
            
            file_entries.append(f'''                <tr>
                    <td><a href="{file_path.name}" class="file-link">{file_path.name}</a></td>
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
            
            file_entries.append(f'''        <a href="{file_path.name}" class="file-item">
            <span class="file-name">{file_path.name}</span>
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
    <h1>{header_title}</h1>
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
  %(prog)s -g "*.html" -g "*.css"            # Only HTML and CSS files
  %(prog)s --sort-by-size-desc               # Largest files first
  %(prog)s -g "*.pdf" --sort-by-time         # Recent PDFs first
  %(prog)s -t "My Files" -o files.html       # Custom title and output name
  %(prog)s -c --sort-by-size                 # Columnar layout, sorted by size
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
    parser.add_argument(
        "-g", "--glob",
        action="append",
        dest="patterns",
        help="Glob pattern to match files (can be used multiple times). Default: all files"
    )
    parser.add_argument(
        "-c", "--columns",
        action="store_true",
        help="Use columnar layout with proper alignment for name, size, and date"
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
        version=f"%(prog)s {VERSION}",
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
    
    # Convert input directory to Path object
    input_dir = Path(args.input_dir).resolve()
    
    # Validate input directory
    if not input_dir.is_dir():
        print(f"Error: Directory '{input_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Set default header if not provided
    header_title = args.header or f"Files in {input_dir.name}"
    
    # Handle glob patterns
    patterns = args.patterns or []
    
    print(f"Scanning directory: {input_dir}")
    if patterns:
        print(f"Using patterns: {', '.join(patterns)}")
    else:
        print("Scanning all files")
    print(f"Sort method: {args.sort_method}")
    
    # Check if any files exist matching the patterns
    matched_files = get_files_by_patterns(input_dir, patterns, args.output)
    
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
        input_dir, args.output, args.title, header_title, patterns, args.sort_method, args.columns
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
    sorted_files = sort_files(matched_files, args.sort_method)
    for i, file_path in enumerate(sorted_files[:5]):
        print(f"  - {file_path.name}")
    
    if len(sorted_files) > 5:
        print(f"  ... and {len(sorted_files) - 5} more")


if __name__ == "__main__":
    main()
