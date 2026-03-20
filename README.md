# helix-sandbox

Extracted sandbox and virtual desktop backend sources from Helix AI Studio.

## Included

- `src/sandbox/*`
- `src/tools/sandbox_pilot_bridge.py`
- `src/utils/subprocess_utils.py`
- `src/utils/platform_utils.py`
- `scripts/wsb_pilot_agent.py`
- sandbox image build scripts

## Current status

This repo now contains the backend-side sandbox logic.
Application-side facades such as `sandbox_service`, `desktop_tool_service`, and UI tabs still live in the main Helix app.
