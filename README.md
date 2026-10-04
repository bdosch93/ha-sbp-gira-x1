# SBP Gira X1 for Home Assistant

Local Home Assistant integration for a Gira X1 using the official Gira IoT
REST API v2. It deliberately does **not** use Home Assistant's KNX integration
and does not require a cloud service or an inbound callback server.

## Supported in 0.3.0

- switches, switched sockets and KNX lights (on/off, brightness and color temperature when exposed)
- covers (open, close, stop, position and slat position when exposed)
- covers shown as **shutters** suppress misleading slat/tilt controls even if
  the Gira project exposes a writable slat-position data point
- heating controls (current temperature and target temperature)
- binary status and numeric/text status functions
- stateless scene-recall buttons for Gira X1 function scenes, scene sets and
  scene extensions;
  the optional scene-teach data point is deliberately never exposed
- Gira GPA location and trade as diagnostic entity attributes
- local polling with a configurable interval

## Security model

Version 0.3.4 adds the explicit diagnostic action `sbp_gira_x1.test_cover_step`.
It writes one binary value (0 or 1) to a selected cover's writable
`Step-Up-Down` point, requiring its expected point UID to match both the
current and bound mappings. It may move the drive. Use only while observing
the device; it performs no retry or automatic reversal. Normal cover actions
remain unchanged. To revert this diagnostic extension, reinstall commit
`e4b59bb` through HACS and restart Home Assistant.

Version 0.3.2 additionally records the last 40 cover write attempts in memory:
time, logical and current point IDs, value, completion stage and exception type.
It never retries commands. This is API-level evidence, not proof of movement.
The history is cleared on restart. Exception messages and tokens are excluded.

Version 0.3.1 adds passive cover diagnostics: logical point IDs, read/write flags,
cached values and per-function error types from the latest poll. Diagnostics do
not send movement commands or perform extra device requests. Error messages and
request URLs are excluded to avoid leaking tokens. Room names and positions are
private household data; review diagnostics before sharing them publicly.

During setup Home Assistant sends the supplied Gira X1 user name and password
directly to the X1's local HTTPS API once. The X1 returns a dedicated 32-character
client token. Only the host and that token are stored in the Home Assistant config
entry. Credentials and tokens must never be committed to this repository.

The X1 uses an appliance certificate that is not publicly trusted; TLS certificate
verification is disabled only for the direct local connection to the configured X1,
as described by Gira's API documentation.

## Installation through HACS

1. HACS → Integrations → Custom repositories.
2. Add `https://github.com/bdosch93/ha-sbp-gira-x1` as category **Integration**.
3. Download **SBP Gira X1** and restart Home Assistant.
4. Settings → Devices & services → Add integration → **SBP Gira X1**.
5. Enter the X1 host/IP and the X1 credentials directly in Home Assistant.

## Sources

- [Gira developer portal](https://partner.gira.com/en/service/software-tools/developer.html)
- [Gira IoT REST API v2 documentation](https://partner.gira.com/data3/Gira_IoT_REST_API_v2_EN.pdf)

This project is independent and is not affiliated with or endorsed by Gira.
