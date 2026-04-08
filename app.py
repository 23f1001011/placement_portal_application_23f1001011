import os
# Load .env file FIRST, before any config imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_mail import Mail
from config import config
from models import db
from models.user import User
from utils.cache import init_redis
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.company import company_bp
from routes.student import student_bp
from celery_tasks.celery_app import init_app as init_celery

# Initialize extensions
jwt = JWTManager()
mail = Mail()
celery = None

def create_app(config_name=None):
    """
    Application factory function.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    print(f"Resolved DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    CORS(app)
    
    # Initialize Redis
    try:
        init_redis(app)
    except Exception as e:
        print(f"Warning: Could not connect to Redis: {e}")
    
    # Initialize Celery with Flask app
    global celery
    celery = init_celery(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(company_bp, url_prefix='/api/company')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        create_admin_user()
    
    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login')
    def login():
        return render_template('login.html')
    
    @app.route('/register')
    def register():
        return render_template('register.html')
    
    @app.route('/dashboard')
    @jwt_required(optional=True)
    def dashboard():
        user_role = ''
        try:
            identity = get_jwt_identity()
            if identity:
                user = User.query.get(int(identity))
                if user:
                    user_role = user.role
        except Exception:
            pass  # No valid token, user_role remains ''
        return render_template('dashboard.html', user_role=user_role)

    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def api_auth_me():
        """Direct api/auth/me endpoint for dashboard compatibility."""
        identity = get_jwt_identity()
        user = User.query.get(int(identity))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user.to_dict()
        if user.role == 'company' and user.company:
            user_data['company'] = user.company.to_dict()
        elif user.role == 'student' and user.student:
            user_data['student'] = user.student.to_dict()
        
        return jsonify(user_data), 200
    
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


def create_admin_user():
    """
    Create admin user if not exists.
    """
    from models.user import User
    from models import db
    
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@placementportal.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully")
    return admin


# Create the application
app = create_app()

# Debug: Print all routes
print("=" * 50)
print("Registered routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint} ({list(rule.methods)})")
print("=" * 50)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

