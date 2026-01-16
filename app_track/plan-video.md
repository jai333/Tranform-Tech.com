# Self-Hosted Video Call Feature – Implementation Plan

## Goal
Enable recruiters and job seekers to join a secure, real-time video meeting from within the ATS/CRM app **without** using third-party SaaS (e.g.0Google Meet, Zoom). All media and signalling must be under our control.

*Two-party calls are the MVP, but the architecture should scale to small group calls (≤ 10) later.*

---

## High-Level Architecture

```
Browser A ──┐                ┌── Browser B
            │  (1) WebSocket │
 Django Channels  <──────────>  Django Channels
 Signalling Server│            │  (2) WebSocket
            └── STUN / TURN  ─┘
                 │   (3) ICE negotiation
                 │
             Peer-to-Peer   (4) SRTP media
             WebRTC Media  <────────────→
```

1. **Signalling** (room, offer/answer, ICE candidates) travels over **Django Channels WebSockets**.
2. **STUN** finds public IPs; **TURN (coturn)** relays in NAT-restricted cases.
3. Peers establish a **WebRTC** connection (DTLS-SRTP encrypted).
4. Media flows peer-to-peer or via TURN if needed.

---

## Tech Stack & Libraries

| Layer                | Choice / Library                                     | Rationale |
|----------------------|------------------------------------------------------|-----------|
| Web Framework        | Django 5.x (existing)                                | Native |
| Real-time transport  | **Django Channels 4** + Redis                        | Reliable WebSocket support |
| Signalling Protocol  | Custom JSON (room, SDP offer/answer, ICE)            | Lightweight |
| WebRTC Front-End     | **simple-peer** (wrapper) + `adapter.js`             | Cross-browser abstraction |
| NAT traversal        | **coturn** (Docker container)                        | OSS, self-hosted TURN/STUN |
| Optional Recording   | **mediasoup-recorder** / FFmpeg on TURN server       | Future work |

---

## Milestone Breakdown

### 1. Infrastructure
1. Add **Redis** service (Docker) for Channels layer.
2. Deploy **coturn** container (`turn:3478`, `stun:3478`).
3. Generate secure `turnserver.conf` (long-term creds). Expose only to app hosts.

### 2. Backend (Django)
1. `pip install channels channels-redis`
2. Configure `ASGI_APPLICATION`, `CHANNEL_LAYERS`.
3. Create **`video/consumers.py`**:
   * `WebRTCConsumer` (JsonWebsocketConsumer)
   * Handles `join`, `offer`, `answer`, `ice`.
4. Use **room UUID** (meeting_id) for group name.
5. Auth: WebSocket connects via **session cookie** & **@login_required**.
6. Permissions: Only interviewer & applicant IDs stored in `Interview` may connect.

### 3. Front-End (Templates/JS)
1. On interview detail page (video type) load `video.js`.
2. `const peer = new SimplePeer({ initiator, trickle: false, config: { iceServers: [...] } });`
3. `peer.on('signal', msg => websocket.send(JSON.stringify({...})))`.
4. Handle inbound WebSocket messages to `peer.signal(data)`.
5. Attach `getUserMedia` streams to `<video>` elements.
6. UI: mute, camera toggle, end call.

### 4. Security Hardening
* **DTLS-SRTP** is intrinsic to WebRTC (E2E when P2P, Relayed-SRTP via TURN).
* Use **TLS** (HTTPS/WSS) everywhere (nginx reverse proxy terminates cert).
* Validate room membership server-side.
* Turn credentials: time-limited via TURN REST API or static long-term with TLS.
* CSP headers to restrict camera/mic usage.
* Rate-limit WebSocket joins.

### 5. DevOps & Deployment
1. Add Docker compose services for `redis`, `coturn`.
2. Add systemd health-check for coturn.
3. Expose TURN TCP/UDP 3478, optionally 5349 TLS.
4. Document firewall rules.

### 6. Testing
* Unit test consumer permission logic.
* Cypress / Playwright e2e: two browsers join room, verify video track flows.
* Latency & packet-loss tests via `webrtc-internals` capture.

### 7. Future Enhancements
* Screen-sharing via `getDisplayMedia`.
* Recording: server-side via [rtp-forwarding to FFmpeg](https://github.com/coturn/coturn/wiki/turnserver#rtp-forwarding).
* Group calls using **SFU** (e.g. mediasoup) replacing P2P when participants >3.
* Text chat overlay via same Channels socket.

---

## File/Module Skeleton
```
tracking_app/
│
├── video/
│   ├── __init__.py
│   ├── routing.py           # websocket url => consumer
│   ├── consumers.py         # WebRTCConsumer
│   └── templates/
│       └── video/
│           └── room.html    # minimal test room
│
├── static/
│   └── js/
│       └── video.js         # simple-peer logic
└── urls.py                  # include("video.urls")
```

---

## Next Steps
1. Review & approve this plan.
2. Bootstrap `video` Django app with Channels config.
3. Integrate signalling UI into interview detail page.
4. Launch internal beta, gather feedback. 