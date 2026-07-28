# Transform.io — Advanced Multi-Tenant ATS, CRM & AI Workflow Platform

An enterprise-grade, multi-tenant Applicant Tracking System (ATS), B2B Sales CRM, and IT Telemetry orchestration platform built with Django. Powered by an autonomous AI recruitment pipeline, two-way isolated tenant mail routing, an Enterprise Developer API & Webhook engine, and a state-of-the-art "Cyber-Nebula" design system.

---

## 🌟 Executive & Enterprise Features

### 1. 🏢 White-Label Multi-Tenant Architecture & Governance
- **Cryptographic Tenant Isolation**: Complete data separation across organizations. Zero cross-tenant data visibility or query leakage enforced at the ORM and SQL database layers.
- **SaaS Admin Portal**: Powerful governance interface for provisioning client companies, custom domain verification, and subscription lifecycle management (Free, Starter, Growth, Enterprise).
- **Tenant Account & Data Manager**: Dedicated workspace portal (`/company/data/`) for organization administrators to generate employee credentials, control dashboard permissions, and oversee company-wide data.

### 2. 📬 Advanced Tenant Mail Integration & Two-Way Sync
- **Dedicated Tenant Mail Hub**: Interactive configuration console accessible directly from the top navigation dropdown, organization portal, and user profile.
- **Registered Corporate Email Scoping**: Custom sender email and display name configuration per organization (`mail_registered_email`), locked strictly to the assigned tenant ID.
- **Two-Way Real-Time Mail Engine**: Seamless SMTP/IMAP configuration with custom routing servers, port controls, and authentication secrets stored under per-tenant encryption scope.
- **Automated Verification & Reply Synchronization**: One-click test email dispatch and automated incoming prospect email synchronization with AI sentiment analysis directly into the **Unified Tenant Inbox**.

### 3. ⚡ Enterprise Developer API & Webhooks Ecosystem
- **Screen-Only UI Dashboards**: Exotic, high-density dashboard visualizations crafted without distracting hardware frames, optimized for developer immersion.
- **Plan-Enforced API Security**: API settings access is restricted exclusively to Enterprise tier accounts, featuring automated interception and upgrade redirection for non-enterprise organizations.
- **Real-Time Webhook Streaming**: Set up endpoint URLs, custom HTTP authentication headers, and event subscriptions (`candidate.hired`, `email.reply_received`, `security.alert`) with interactive JSON payload simulators and live delivery status logs.
- **API Key Management**: Instant generation and revocation of secure corporate API keys with rate limit tracking and usage analytics.

### 4. 🧠 Autonomous AI Pipeline & Universal Command Bar
- **Universal Command Palette (`Cmd+K` / `Ctrl+K`)**: Global instant semantic navigation across C-Suite reporting, ATS pipelines, sales accounts, IT helpdesk tickets, and developer documentation.
- **AI Resume & Candidate Matching**: Automated resume parsing, skills extraction, and algorithmic job match scoring.
- **Interactive Interview Scorecards**: Comprehensive candidate evaluation criteria with automated sentiment AI and structured hiring workflows.

### 5. 🎨 Exotic Cyber-Nebula UI & Dynamic Theme Persistence
- **State-of-the-Art Visual Design**: Sleek dark mode aesthetics, vibrant neon cyan (`#00E5FF`) and indigo gradients, glassmorphism containers, and reactive micro-animations.
- **Standardized Action Buttons**: Perfectly aligned typography, drop shadows, and zero-border finishing across all showcase action triggers (*Open AI Pipeline*, *Access Sales Dashboard*, *Try Cmd+K Now*, *Explore Developer Settings*).
- **Zero-FOUC Theme Switching**: Dual-layer synchronization script utilizing early DOM tree evaluation and click-deduplication logic to switch smoothly between Light and Dark cyber themes without screen flash or double-toggles.

### 6. 🛡️ IT Telemetry & Cybersecurity Dashboard
- **Security Incident Orchestration**: Real-time threat detection, active vulnerability reporting, IP blocklisting, and simulated phishing awareness protocols.
- **IT Helpdesk & Asset Inventory**: Full internal service desk supporting ticket tracking, customer satisfaction (CSAT) scorecards, vendor management, and employee hardware asset assignation.

### 7. 📦 Bulk Import/Export & Executive Analytics
- **Template Download & Import**: One-click download for clean CSV templates and drag-and-drop bulk importation for IT assets, candidate resumes, and client sales rosters.
- **Executive Reporting Hub**: Automated report scheduling, conversion metrics, and multi-dimensional analytics.

---

## 🛠️ Technology Stack

- **Backend Architecture**: Django 5.2 (Python 3.8+)
- **Frontend & Styling**: Vanilla CSS3 Custom Tokens, HTML5 Semantic Layouts, Responsive JS, Cyber-Nebula Design System
- **Database Architecture**: SQLite (Development with scoped Tenant Foreign Keys) / PostgreSQL (Production)
- **Async & WebSockets**: Django Channels + Daphne ASGI server for real-time telemetry and unified inbox feeds
- **Video & Collaboration**: HTML5 WebRTC embedded video conferencing

---

## 🚀 Installation & Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/jai333/ATS-CRM-Transform.io.git
   cd ATS-CRM-Transform.io/app_track
   ```

2. **Create and activate your virtual environment**
   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\Activate.ps1
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install enterprise dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply multi-tenant database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create administrative superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Launch the development server**
   ```bash
   python manage.py runserver 8000
   ```

7. **Access Application Ecosystem**:
   - Main Platform & Dashboard: http://127.0.0.1:8000/
   - SaaS Admin & Tenant Lifecycle Portal: http://127.0.0.1:8000/saas-admin/
   - Unified Tenant Mailbox: http://127.0.0.1:8000/inbox/
   - Django Admin Engine: http://127.0.0.1:8000/admin/

---

## 🗺️ Product Roadmap & Progress

- [x] Advanced candidate matching with AI & instant resume parsing
- [x] White-label Multi-Tenant architecture & zero-leakage data isolation
- [x] Advanced Tenant Mail Integration with customizable SMTP scopes & two-way synchronization
- [x] Enterprise Developer API & real-time Webhook simulation console
- [x] Bulk CSV import/export engines for HR, Sales, and IT inventories
- [x] Advanced executive reporting, automated scheduled reports, and telemetry dashboards
- [x] Universal AI Command Palette (`Cmd+K`) and zero-FOUC theme toggling
- [ ] Mobile native applications (iOS / Android)
- [ ] SAML / SSO Enterprise Federation (Okta / Azure AD)

---

## 📜 Legal & Licensing

This platform is released under a **Dual License Model**:

### 🔒 Primary License: PROPRIETARY (Default)
See `PROPRIETARY_LICENSE.txt` for legal terms.
- **This software is proprietary and confidential.**
- Restricted exclusively to authorized organizations and assigned tenants.
- Unauthorized copying, distribution, modification, or commercial sublicensing is strictly prohibited.
- Licensing inquiries: `it@transform.io`

### 📜 Secondary License: APACHE 2.0 (Conditional Option)
See `LICENSE` file for details. Available only under express legal grant by Transform.io LLP.

**Copyright © 2026 Transform.io LLP. All rights reserved.**

---

## 🏢 Contact & Enterprise Support

- **Email**: it@transform.io
- **Phone**: +91 9664131355
- **Headquarters**: 4th Floor, Jaipur Centre, 420, Tonk Rd, Durgapura, Jaipur, Rajasthan 302018

---

## 📈 Changelog

### v2.5.0 — Enterprise Evolution & Advanced Integrations (July 2026)
- **Advanced Tenant Mail Option Hub**: Added direct mail integration consoles in tenant accounts and profiles with strict organization scoping and test outbound verification.
- **Enterprise API & Webhooks Engine**: Introduced screen-only interactive API dashboards with subscription enforcement and real-time webhook payload streaming.
- **Cyber-Nebula UI Polish**: Standardized showcase action buttons and completely eliminated Flash of Unstyled Content (FOUC) during light/dark theme switching.
- **Enhanced Navigation**: Integrated interactive floating command pills and unified user account menu options.

### v1.0.0 — Core Foundation (January 2026)
- Initial platform release featuring core Applicant Tracking System (ATS), B2B CRM, WebRTC video interviews, and real-time notifications.

---
**Crafted with excellence by Transform.io LLP Engineering Team**
