#!/bin/bash
# VPSWeb Development Server Stop Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default port
PORT=8000
HOST="127.0.0.1"
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Gracefully stop the VPSWeb development server"
            echo ""
            echo "Options:"
            echo "  -p, --port PORT    Port number (default: 8000)"
            echo "  -h, --host HOST    Host address (default: 127.0.0.1)"
            echo "  -f, --force        Force kill without graceful shutdown"
            echo "      --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Stop server on default port 8000"
            echo "  $0 -p 8080         # Stop server on port 8080"
            echo "  $0 --force         # Force kill the server"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Stopping VPSWeb development server on $HOST:$PORT..."

# Function to find and stop the uvicorn process
stop_server() {
    local port=$1
    local force=${2:-false}

    # Find process ID of uvicorn running on the specified port
    local pid
    pid=$(lsof -ti:"$port" 2>/dev/null || true)

    if [[ -z "$pid" ]]; then
        echo "No server process found running on port $port"
        return 1
    fi

    # Check if it's actually a uvicorn process
    local process_name
    process_name=$(ps -p "$pid" -o comm= 2>/dev/null || true)

    if [[ ! "$process_name" =~ (uvicorn|python) ]]; then
        echo "Process $pid on port $port is not a uvicorn server: $process_name"
        return 1
    fi

    echo "Found uvicorn server process: $pid ($process_name)"

    if [[ "$force" == "true" ]]; then
        echo "Force killing server process $pid..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1

        # Verify it's stopped
        if kill -0 "$pid" 2>/dev/null; then
            echo "Failed to kill process $pid"
            return 1
        else
            echo "Server process $pid force killed successfully"
            return 0
        fi
    else
        # Try graceful shutdown first
        echo "Attempting graceful shutdown of process $pid..."
        kill -TERM "$pid" 2>/dev/null || true

        # Wait for graceful shutdown
        local count=0
        while [[ $count -lt 10 ]]; do
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "Server process $pid stopped gracefully"
                return 0
            fi
            sleep 1
            ((count++))
            echo "Waiting for server to stop... ($count/10)"
        done

        # If graceful shutdown didn't work, force kill
        echo "Graceful shutdown timed out, force killing process $pid..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1

        if kill -0 "$pid" 2>/dev/null; then
            echo "Failed to kill process $pid"
            return 1
        else
            echo "Server process $pid force killed after timeout"
            return 0
        fi
    fi
}

# Additional method: try to find uvicorn processes by command line
find_uvicorn_by_cmd() {
    local force=${1:-false}
    local pids
    pids=$(pgrep -f "uvicorn.*vpsweb.webui.main:app" 2>/dev/null || true)

    if [[ -z "$pids" ]]; then
        echo "No uvicorn VPSWeb processes found by command line"
        return 1
    fi

    echo "Found uvicorn VPSWeb processes: $pids"

    local stopped=false
    for pid in $pids; do
        if [[ "$force" == "true" ]]; then
            echo "Force killing uvicorn process $pid..."
            kill -9 "$pid" 2>/dev/null || true
        else
            echo "Stopping uvicorn process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
        fi
        stopped=true
    done

    if [[ "$stopped" == "true" ]]; then
        if [[ "$force" != "true" ]]; then
            echo "Waiting for processes to stop..."
            sleep 2
        fi
        echo "VPSWeb server processes stopped"
        return 0
    fi

    return 1
}

# Try multiple methods to stop the server
stopped=false

# Method 1: Stop by port
if stop_server "$PORT" "$FORCE"; then
    stopped=true
fi

# Method 2: If not stopped, try by command line
if [[ "$stopped" != "true" ]]; then
    echo "Trying alternative method to find server processes..."
    if find_uvicorn_by_cmd "$FORCE"; then
        stopped=true
    fi
fi

# Final status
if [[ "$stopped" == "true" ]]; then
    echo ""
    echo "✅ VPSWeb development server stopped successfully"
    echo "   Server was running on $HOST:$PORT"
else
    echo ""
    echo "❌ No VPSWeb server process found running on $HOST:$PORT"
    echo "   The server might not be running or is on a different port"
    echo ""
    echo "To find running servers:"
    echo "  ps aux | grep uvicorn"
    echo "  lsof -i :8000"
    exit 1
fi

# Optional: Clean up any leftover temporary files
echo "Cleaning up temporary files..."
find /tmp -name "uvicorn.*" -user "$(whoami)" -type f -delete 2>/dev/null || true

echo "Done! 🎉"