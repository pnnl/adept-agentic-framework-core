.PHONY: all install render clean help

# Default target
all: render

# Install mermaid-cli locally
install:
	@echo "Installing mermaid-cli locally..."
	npm install
	@echo ""
	@echo "✓ Installation complete!"
	@echo ""
	@echo "To use the local installation, the scripts will automatically detect it."
	@echo "Or you can add to your PATH:"
	@echo "  export PATH=\"\$$PATH:\$$(pwd)/node_modules/.bin\""
	@echo ""

# Install mermaid-cli globally
install-global:
	@echo "Installing mermaid-cli globally..."
	npm install -g @mermaid-js/mermaid-cli
	@echo ""
	@echo "✓ Global installation complete!"
	@echo "You can now use 'mmdc' from anywhere."
	@echo ""

# Render diagrams using bash script (preferred on Linux/macOS)
render:
	@echo "Rendering diagrams with bash script..."
	./render-diagrams.sh

# Render diagrams using Python script (cross-platform)
render-python:
	@echo "Rendering diagrams with Python script..."
	python3 render-diagrams.py

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf diagrams .tmp
	@echo "✓ Clean complete!"

# Clean everything including node_modules
clean-all: clean
	@echo "Removing node_modules..."
	rm -rf node_modules package-lock.json
	@echo "✓ Full clean complete!"

# Show help
help:
	@echo "ADEPT Workshop Diagram Rendering"
	@echo ""
	@echo "Available targets:"
	@echo "  make install         - Install mermaid-cli locally (in node_modules)"
	@echo "  make install-global  - Install mermaid-cli globally (requires permissions)"
	@echo "  make render          - Render all diagrams (using bash script)"
	@echo "  make render-python   - Render all diagrams (using Python script)"
	@echo "  make clean           - Remove generated diagram files"
	@echo "  make clean-all       - Remove generated files and node_modules"
	@echo "  make help            - Show this help message"
	@echo ""
	@echo "Output:"
	@echo "  Diagrams are rendered to ./diagrams/"
	@echo "  - diagram_01.png, diagram_01.svg"
	@echo "  - diagram_02.png, diagram_02.svg"
	@echo "  - etc."
	@echo ""
	@echo "Requirements:"
	@echo "  - Node.js (for npm)"
	@echo "  - Python 3 (for Python script)"
	@echo ""
