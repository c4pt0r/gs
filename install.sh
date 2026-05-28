#!/bin/bash
#
# Installation script for gmail
# This script installs gmail and its dependencies
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default installation directory
DEFAULT_INSTALL_DIR="$HOME/.local/gmail"
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
BIN_LINK_DIR="$HOME/.local/bin"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "python3 is not installed"
        exit 1
    fi

    # Check Python version (need 3.8.1+)
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    print_info "Found python3: $PYTHON_VERSION"

    # Check if version is >= 3.8.1
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8, 1) else 1)' 2>/dev/null; then
        print_error "Python 3.8.1 or higher is required (found: $PYTHON_VERSION)"
        exit 1
    fi
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is required for installation"
        print_info "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_info "Found uv: $(uv --version)"
}

install_gmail() {
    print_info "Installing gmail to $INSTALL_DIR..."
    cd "$SCRIPT_DIR"

    # Remove old installation if exists
    if [ -d "$INSTALL_DIR" ]; then
        print_warn "Removing old installation..."
        rm -rf "$INSTALL_DIR"
    fi

    # Create installation directory
    mkdir -p "$INSTALL_DIR"

    # Copy project files
    print_info "Copying project files..."
    cp -r gmail "$INSTALL_DIR/"
    cp pyproject.toml "$INSTALL_DIR/"
    cp README.md "$INSTALL_DIR/" 2>/dev/null || true
    cp LICENSE "$INSTALL_DIR/" 2>/dev/null || true

    # Create virtual environment and install dependencies
    print_info "Creating virtual environment and installing dependencies..."
    cd "$INSTALL_DIR"
    uv venv
    uv pip install -e .

    # Create wrapper script
    print_info "Creating launcher script..."
    cat > "$INSTALL_DIR/gmail-run" << EOF
#!/bin/bash
source "$INSTALL_DIR/.venv/bin/activate"
exec python -m gmail.cli "\$@"
EOF
    chmod +x "$INSTALL_DIR/gmail-run"

    # Create symlink in bin directory
    mkdir -p "$BIN_LINK_DIR"
    ln -sf "$INSTALL_DIR/gmail-run" "$BIN_LINK_DIR/gmail"

    print_info "Installation complete!"
    print_info "Installed to: $INSTALL_DIR"
    print_info "Symlinked to: $BIN_LINK_DIR/gmail"
}

check_path() {
    if [[ ":$PATH:" != *":$BIN_LINK_DIR:"* ]]; then
        print_warn "$BIN_LINK_DIR is not in your PATH"
        print_warn "Add the following line to your ~/.bashrc or ~/.zshrc:"
        echo ""
        echo "    export PATH=\"$BIN_LINK_DIR:\$PATH\""
        echo ""
    fi
}

show_usage() {
    echo "gmail installation script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dir DIR    Installation directory (default: $DEFAULT_INSTALL_DIR)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  INSTALL_DIR      Override installation directory"
    echo ""
    echo "Examples:"
    echo "  $0                              # Install to $DEFAULT_INSTALL_DIR"
    echo "  $0 -d /opt/gmail           # Install to /opt/gmail"
    echo "  INSTALL_DIR=~/apps/gmail $0 # Install to ~/apps/gmail"
    echo ""
    echo "Note: A symlink will be created in $BIN_LINK_DIR/gmail"
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    print_info "gmail installer"
    print_info "Installation directory: $INSTALL_DIR"
    print_info "Symlink directory: $BIN_LINK_DIR"
    echo ""

    check_python
    check_uv
    install_gmail
    check_path

    echo ""
    print_info "Run 'gmail --help' to get started"
    print_info "Requirements: Python 3.8.1+"
    print_info ""
    print_info "Next steps:"
    print_info "  1. Set up Google API credentials (see README.md)"
    print_info "  2. Run: gmail --credentials credentials.json repl"
}

main "$@"
