from datetime import datetime
from models import db
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

class User(db.Model):
    """Base User model for all roles."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, company, student
    is_active = db.Column(db.Boolean, default=True)
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='user', uselist=False, lazy=True)
    student = db.relationship('Student', backref='user', uselist=False, lazy=True)
    
    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if the provided password matches."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'is_blacklisted': self.is_blacklisted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<User {self.username} - {self.role}>'
