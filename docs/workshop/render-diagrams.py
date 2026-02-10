#!/usr/bin/env python3
"""
Script to render all Mermaid diagrams from ADEPT-Workshop-Diagrams.md
Requires: @mermaid-js/mermaid-cli (mmdc) installed globally or locally
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    BLUE = '\033[1;34m'
    GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[1;31m'
    NC = '\033[0m'


def print_header(message: str) -> None:
    """Print a blue header message"""
    print(f"{Colors.BLUE}{'=' * 64}{Colors.NC}")
    print(f"{Colors.BLUE}  {message}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 64}{Colors.NC}")
    print()


def print_success(message: str) -> None:
    """Print a green success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str) -> None:
    """Print a red error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_warning(message: str) -> None:
    """Print a yellow warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def check_mmdc() -> Tuple[bool, str]:
    """Check if mmdc (mermaid-cli) is installed"""
    # Check in PATH
    try:
        result = subprocess.run(
            ['mmdc', '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return True, 'mmdc (in PATH)'
    except FileNotFoundError:
        pass

    # Check in local node_modules
    script_dir = Path(__file__).parent
    local_mmdc = script_dir / 'node_modules' / '.bin' / 'mmdc'
    if local_mmdc.exists():
        return True, str(local_mmdc)

    return False, ''


def extract_mermaid_diagrams(source_file: Path) -> List[Tuple[int, str]]:
    """
    Extract all Mermaid diagram code blocks from markdown file
    Returns list of (diagram_number, diagram_code) tuples
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all mermaid code blocks
    pattern = r'```mermaid\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    return [(i + 1, code.strip()) for i, code in enumerate(matches)]


def render_diagram(
    mmdc_path: str,
    diagram_code: str,
    output_png: Path,
    output_svg: Path
) -> Tuple[bool, bool]:
    """
    Render a single Mermaid diagram to PNG and SVG
    Returns (png_success, svg_success)
    """
    # Create temporary mmd file
    temp_mmd = output_png.parent / '.tmp.mmd'
    with open(temp_mmd, 'w', encoding='utf-8') as f:
        f.write(diagram_code)

    png_success = False
    svg_success = False

    try:
        # Render PNG
        result = subprocess.run(
            [
                mmdc_path,
                '-i', str(temp_mmd),
                '-o', str(output_png),
                '-b', 'transparent',
                '-w', '1920',
                '-H', '1080',
                '--scale', '2'
            ],
            capture_output=True,
            text=True,
            check=False
        )
        png_success = result.returncode == 0

        # Render SVG
        if png_success:
            result = subprocess.run(
                [
                    mmdc_path,
                    '-i', str(temp_mmd),
                    '-o', str(output_svg),
                    '-b', 'transparent'
                ],
                capture_output=True,
                text=True,
                check=False
            )
            svg_success = result.returncode == 0

    finally:
        # Clean up temp file
        if temp_mmd.exists():
            temp_mmd.unlink()

    return png_success, svg_success


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def main():
    """Main rendering function"""
    print_header("ADEPT Workshop - Mermaid Diagram Renderer")

    # Check for mmdc
    mmdc_available, mmdc_path = check_mmdc()
    if not mmdc_available:
        print_error("mermaid-cli (mmdc) not found")
        print()
        print("Install it with:")
        print("  npm install -g @mermaid-js/mermaid-cli")
        print()
        print("Or install locally in this directory:")
        script_dir = Path(__file__).parent
        print(f"  cd {script_dir}")
        print("  npm install")
        print()
        sys.exit(1)

    print_success(f"Found mmdc: {mmdc_path}")
    print()

    # Setup paths
    script_dir = Path(__file__).parent
    source_file = script_dir / 'ADEPT-Workshop-Diagrams.md'
    output_dir = script_dir / 'diagrams'

    # Check source file
    if not source_file.exists():
        print_error(f"Source file not found: {source_file}")
        sys.exit(1)

    print_success(f"Found source file: {source_file}")
    print()

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Extract diagrams
    print(f"{Colors.BLUE}Extracting Mermaid diagrams...{Colors.NC}")
    diagrams = extract_mermaid_diagrams(source_file)

    if not diagrams:
        print_error("No Mermaid diagrams found in source file")
        sys.exit(1)

    print_success(f"Extracted {len(diagrams)} diagrams")
    print()

    # Render each diagram
    print(f"{Colors.BLUE}Rendering diagrams...{Colors.NC}")
    print()

    success_count = 0
    fail_count = 0

    for diagram_num, diagram_code in diagrams:
        output_png = output_dir / f"diagram_{diagram_num:02d}.png"
        output_svg = output_dir / f"diagram_{diagram_num:02d}.svg"

        print(f"  Rendering diagram {diagram_num:02d}... ", end='', flush=True)

        png_ok, svg_ok = render_diagram(mmdc_path, diagram_code, output_png, output_svg)

        if png_ok and svg_ok:
            print(f"{Colors.GREEN}✓ PNG + SVG{Colors.NC}")
            success_count += 1
        elif png_ok:
            print(f"{Colors.YELLOW}✓ PNG only (SVG failed){Colors.NC}")
            success_count += 1
        else:
            print(f"{Colors.RED}✗ Failed{Colors.NC}")
            fail_count += 1

    print()
    print_header("Rendering complete!")

    print("Summary:")
    print(f"  Success: {success_count} diagrams")
    if fail_count > 0:
        print(f"  {Colors.RED}Failed:  {fail_count} diagrams{Colors.NC}")
    print()

    print(f"Output directory: {output_dir}")
    print()

    # List generated files
    png_files = sorted(output_dir.glob('diagram_*.png'))
    if png_files:
        print("Files generated:")
        for png_file in png_files:
            size = format_file_size(png_file.stat().st_size)
            print(f"  {png_file.name} ({size})")

            svg_file = png_file.with_suffix('.svg')
            if svg_file.exists():
                svg_size = format_file_size(svg_file.stat().st_size)
                print(f"  {svg_file.name} ({svg_size})")
        print()

    print(f"{Colors.BLUE}{'=' * 64}{Colors.NC}")

    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
