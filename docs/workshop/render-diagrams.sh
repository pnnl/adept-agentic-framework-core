#!/bin/bash
# Script to render all Mermaid diagrams from ADEPT-Workshop-Diagrams.md
# Requires: @mermaid-js/mermaid-cli (mmdc)

set -e

BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/ADEPT-Workshop-Diagrams.md"
OUTPUT_DIR="$SCRIPT_DIR/diagrams"
TEMP_DIR="$SCRIPT_DIR/.tmp"

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  ADEPT Workshop - Mermaid Diagram Renderer${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# Check if mmdc is installed
if ! command -v mmdc &> /dev/null; then
    echo -e "${RED}Error: mermaid-cli (mmdc) not found${NC}"
    echo ""
    echo "Install it with:"
    echo "  npm install -g @mermaid-js/mermaid-cli"
    echo ""
    echo "Or install locally in this directory:"
    echo "  cd $SCRIPT_DIR"
    echo "  npm install"
    echo "  export PATH=\"\$PATH:$SCRIPT_DIR/node_modules/.bin\""
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Found mmdc: $(which mmdc)${NC}"
echo ""

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}Error: Source file not found: $SOURCE_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found source file: $SOURCE_FILE${NC}"
echo ""

# Create output and temp directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$TEMP_DIR"

echo -e "${BLUE}Extracting Mermaid diagrams...${NC}"

# Extract all mermaid code blocks
# This awk script extracts content between ```mermaid and ``` markers
awk '
    /^```mermaid/ {
        in_block = 1
        block_num++
        filename = sprintf("'"$TEMP_DIR"'/diagram_%02d.mmd", block_num)
        next
    }
    /^```/ && in_block {
        in_block = 0
        next
    }
    in_block {
        print > filename
    }
' "$SOURCE_FILE"

DIAGRAM_COUNT=$(find "$TEMP_DIR" -name "diagram_*.mmd" 2>/dev/null | wc -l)

if [ "$DIAGRAM_COUNT" -eq 0 ]; then
    echo -e "${RED}Error: No Mermaid diagrams found in source file${NC}"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo -e "${GREEN}✓ Extracted $DIAGRAM_COUNT diagrams${NC}"
echo ""

# Render each diagram
echo -e "${BLUE}Rendering diagrams...${NC}"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for mmd_file in "$TEMP_DIR"/diagram_*.mmd; do
    basename=$(basename "$mmd_file" .mmd)
    number=$(echo "$basename" | sed 's/diagram_//')

    png_file="$OUTPUT_DIR/diagram_${number}.png"
    svg_file="$OUTPUT_DIR/diagram_${number}.svg"

    echo -n "  Rendering diagram $number... "

    # Render PNG (transparent background, high resolution)
    if mmdc -i "$mmd_file" -o "$png_file" \
        -b transparent \
        -w 1920 \
        -H 1080 \
        --scale 2 \
        > /dev/null 2>&1; then

        # Render SVG
        if mmdc -i "$mmd_file" -o "$svg_file" \
            -b transparent \
            > /dev/null 2>&1; then

            echo -e "${GREEN}✓ PNG + SVG${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo -e "${YELLOW}✓ PNG only (SVG failed)${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        fi
    else
        echo -e "${RED}✗ Failed${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

# Clean up temp files
rm -rf "$TEMP_DIR"

echo ""
echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}Rendering complete!${NC}"
echo ""
echo "Summary:"
echo "  Success: $SUCCESS_COUNT diagrams"
if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "  ${RED}Failed:  $FAIL_COUNT diagrams${NC}"
fi
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Files generated:"
ls -lh "$OUTPUT_DIR"/*.png 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo -e "${BLUE}================================================================${NC}"
