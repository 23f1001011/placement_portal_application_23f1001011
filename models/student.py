from datetime import datetime
from models import db

class Student(db.Model):
    """Student model for student profile information."""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    branch = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    resume_url = db.Column(db.String(500))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    skills = db.Column(db.Text)  # Comma-separated skills
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='student', lazy=True)
    
    def to_dict(self):
        """Convert student to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'roll_number': self.roll_number,
            'email': self.email,
            'phone': self.phone,
            'branch': self.branch,
            'year': self.year,
            'cgpa': self.cgpa,
            'resume_url': self.resume_url,
            'skills': self.skills,
            'is_blacklisted': self.is_blacklisted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Student {self.roll_number} - {self.full_name}>'
