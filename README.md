# placement_portal_application_23f1001011[README.md](https://github.com/user-attachments/files/26563952/README.md)
# Placement Portal Application

A comprehensive web application for managing placement activities, connecting students, companies, and administrators in a streamlined placement process.

## Features

### For Students
- User registration and authentication
- Profile management
- View available placement drives
- Apply for job positions
- Track application status
- Dashboard with application overview

### For Companies
- Company registration and verification
- Post job openings and placement drives
- Review student applications
- Shortlist and select candidates
- Manage drive schedules

### For Administrators
- User management (students, companies, admins)
- Drive management and oversight
- Application review and approval
- System analytics and reporting
- User role management

## Technology Stack

### Backend
- **Flask** - Web framework
- **SQLAlchemy** - Database ORM
- **Flask-JWT-Extended** - JWT authentication
- **Flask-Cors** - Cross-origin resource sharing
- **Flask-Bcrypt** - Password hashing
- **Celery** - Background task processing
- **Redis** - Message broker and caching

### Frontend
- **Vue.js** - Progressive JavaScript framework
- **Bootstrap** - CSS framework
- **Axios** - HTTP client
- **HTML5/CSS3** - Frontend markup and styling

### Database
- **SQLite** (development) / **PostgreSQL** (production)

## Project Structure

```
placement_portal_application/
├── app.py                 # Main Flask application
├── celery_worker.py       # Celery worker configuration
├── config.py             # Application configuration
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├──
├── models/               # Database models
│   ├── __init__.py
│   ├── user.py          # User model
│   ├── student.py       # Student model
│   ├── company.py       # Company model
│   ├── drive.py         # Placement drive model
│   └── application.py   # Application model
│
├── routes/               # API routes
│   ├── __init__.py
│   ├── auth.py          # Authentication routes
│   ├── admin.py         # Admin routes
│   ├── student.py       # Student routes
│   └── company.py       # Company routes
│
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── index.html       # Home page
│   ├── login.html       # Login page
│   ├── register.html    # Registration page
│   └── dashboard.html   # Dashboard page
│
├── static/               # Static assets
│   ├── css/
│   │   └── styles.css   # Custom styles
│   └── js/
│       ├── main.js      # Main JavaScript
│       ├── vue.global.js # Vue.js library
│       └── axios.min.js # Axios library
│
├── utils/                # Utility functions
│   ├── __init__.py
│   ├── cache.py         # Caching utilities
│   └── validators.py    # Input validation
│
├── celery_tasks/         # Background tasks
│   ├── __init__.py
│   ├── celery_app.py    # Celery app configuration
│   └── tasks.py         # Task definitions
│
└── instance/             # Instance-specific files
```

## Installation

### Prerequisites
- Python 3.8+
- Redis (for Celery)
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd placement_portal_application
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   DATABASE_URL=sqlite:///app.db
   REDIS_URL=redis://localhost:6379/0
   FLASK_ENV=development
   ```

5. **Initialize the database**
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. **Start Redis server**
   Make sure Redis is running on your system.

7. **Run the application**
   ```bash
   # Start Flask app
   python app.py

   # In another terminal, start Celery worker
   celery -A celery_worker.celery_app worker --pool=solo --loglevel=info

   # In another terminal, start Celery Beat for scheduled tasks
   celery -A celery_worker.celery_app beat --loglevel=info
   ```

8. **Access the application**
   Open your browser and go to `http://localhost:5000`

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user info

### Students
- `GET /api/students/profile` - Get student profile
- `PUT /api/students/profile` - Update student profile
- `GET /api/students/drives` - Get available drives
- `POST /api/students/apply` - Apply for a drive

### Companies
- `GET /api/companies/profile` - Get company profile
- `PUT /api/companies/profile` - Update company profile
- `POST /api/companies/drives` - Create new drive
- `GET /api/companies/applications` - Get applications for company's drives

### Admin
- `GET /api/admin/users` - Get all users
- `GET /api/admin/drives` - Get all drives
- `PUT /api/admin/users/{id}/status` - Update user status
- `DELETE /api/admin/drives/{id}` - Delete drive

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
```

### Database Migrations
```bash
flask db migrate -m "Migration message"
flask db upgrade
```

## Deployment

### Production Setup
1. Set `FLASK_ENV=production` in environment variables
2. Use a production WSGI server like Gunicorn
3. Set up a reverse proxy with Nginx
4. Configure proper database (PostgreSQL recommended)
5. Set up monitoring and logging

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@placementportal.com or create an issue in the repository.

## Changelog

### Version 1.0.0
- Initial release
- Basic user authentication
- Student, company, and admin roles
- Placement drive management
- Application tracking
