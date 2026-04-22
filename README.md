# Transform.io ATS & CRM System

An advanced Applicant Tracking System (ATS) and Customer Relationship Management (CRM) platform built with Django, featuring job management, candidate tracking, interviews, video conferencing, and real-time notifications.

## Project Overview

**Transform.io ATS & CRM** is a comprehensive recruitment and client management system designed for staffing agencies and recruitment firms. It streamlines the entire hiring process from job posting to candidate placement.

### Key Features

- 📋 **Job Management** - Post and manage job openings
- 👥 **Candidate Tracking** - Track candidates through the hiring pipeline
- 📞 **Interview Management** - Schedule and conduct interviews
- 📹 **Video Conferencing** - Built-in video interview capabilities
- 🔔 **Real-time Notifications** - Stay updated on important events
- 💬 **Chat System** - Communication between team members
- 📊 **Application Analytics** - Track application flow and metrics
- 👤 **Candidate Profiles** - Comprehensive candidate information management

## Technology Stack

- **Backend**: Django 5.2
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Database**: SQLite (Development), PostgreSQL (Production)
- **Async**: Django Channels with Daphne ASGI server
- **Real-time**: WebSockets for live updates
- **Video**: HTML5 WebRTC integration

## Installation & Setup

### Prerequisites
- Python 3.8+
- Virtual Environment (recommended)
- pip

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/jai333/ATS-CRM-Transform.io.git
   cd ATS-CRM-Transform.io/app_track
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   # On Windows
   .\.venv\Scripts\Activate.ps1
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver 8000
   ```

7. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## License

This project is released under a **Dual License Model**:

### 🔒 Primary License: PROPRIETARY
See `PROPRIETARY_LICENSE.txt` for details.

**This software is proprietary and confidential.**
- Restricted to authorized use only
- No distribution, sublicensing, or commercial use
- For inquiries: it@transform.io

### 📜 Secondary License: APACHE 2.0 (Optional)
See `LICENSE` file for details.

**Available only if explicitly granted by Transform.io LLP.**
- Permissive with patent protection
- Allows modification and distribution under specific conditions

## Copyright

**Copyright © 2026 Transform.io LLP. All rights reserved.**

This software is protected under:
- Indian Copyright Law
- Proprietary License Agreement
- Apache License 2.0 (conditional)

For complete legal terms, see `COPYRIGHT.md`

## Contact & Support

- **Email**: it@transform.io
- **Phone**: 9664131355
- **Address**: 4th floor, Jaipur Centre, 420, Tonk Rd, Durgapura, Jaipur, Rajasthan 302018

## Security

If you discover a security vulnerability, please email it@transform.io instead of using the issue tracker.

## Roadmap

- [ ] Advanced candidate matching with AI
- [ ] Email integration and automation
- [ ] Bulk import/export functionality
- [ ] Advanced reporting and analytics
- [ ] Mobile app (iOS/Android)
- [ ] SAML/SSO integration

## Project Structure

```
app_track/
├── ats_crm_project/       # Django project settings
├── tracking_app/          # Main application
│   ├── templates/         # HTML templates
│   ├── static/            # CSS, JS, images
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── urls.py            # URL routing
│   └── forms.py           # Form definitions
├── video/                 # Video conferencing app
├── manage.py              # Django management script
└── requirements.txt       # Python dependencies
```

## Development

### Running Tests
```bash
python manage.py test
```

### Code Quality
Ensure code follows PEP 8 standards.

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Contributing

This is a proprietary project. Contributions are by invitation only. Contact it@transform.io for collaboration inquiries.

## Changelog

### v1.0.0 (January 2026)
- Initial release
- Core ATS functionality
- Video interviewing
- Real-time notifications
- Chat system

---

**Made with ❤️ by Transform.io LLP**
