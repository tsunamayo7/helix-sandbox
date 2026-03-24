#!/bin/bash
# helix-sandbox — Container entrypoint
# Starts Xvfb + xfce4 + x11vnc + noVNC

set -e

# Parse resolution
RES="${RESOLUTION:-1280x720x24}"
WIDTH=$(echo "$RES" | cut -dx -f1)
HEIGHT=$(echo "$RES" | cut -dx -f2)
DEPTH=$(echo "$RES" | cut -dx -f3)

echo "[helix-sandbox] Starting virtual display: ${WIDTH}x${HEIGHT}x${DEPTH}"

# Start Xvfb (virtual framebuffer)
Xvfb :99 -screen 0 "${WIDTH}x${HEIGHT}x${DEPTH}" -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to be ready
for i in $(seq 1 20); do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "[helix-sandbox] Xvfb ready after ${i}s"
        break
    fi
    sleep 0.5
done

export DISPLAY=:99

# Start xfce4 desktop
startxfce4 &
XFCE_PID=$!

# Wait for desktop to be ready (wait for a visible window)
echo "[helix-sandbox] Waiting for desktop..."
for i in $(seq 1 30); do
    # Check if any window is visible (desktop panel, etc.)
    WINDOWS=$(xdotool search --onlyvisible --name '' 2>/dev/null | wc -l)
    if [ "$WINDOWS" -gt "2" ]; then
        echo "[helix-sandbox] Desktop ready (${WINDOWS} windows) after ${i}s"
        break
    fi
    sleep 1
done

# Open a terminal to ensure something is rendered
xfce4-terminal --geometry=80x24+50+50 &
sleep 1

# Start x11vnc
VNC_ARGS="-display :99 -forever -shared -noxdamage -noxfixes"
if [ -n "$VNC_PASSWORD" ]; then
    mkdir -p /root/.vnc
    x11vnc -storepasswd "$VNC_PASSWORD" /root/.vnc/passwd
    VNC_ARGS="$VNC_ARGS -rfbauth /root/.vnc/passwd"
fi
x11vnc $VNC_ARGS -rfbport 5900 &
sleep 1

# Start noVNC (websocket proxy for browser access)
echo "[helix-sandbox] Starting noVNC on port 6080"
websockify --web /usr/share/novnc 6080 localhost:5900 &

echo "[helix-sandbox] Ready — VNC: 5900, NoVNC: 6080"

# Keep container running
wait
