from datetime import datetime
from models import db

class Company(db.Model):
    """Company model for company profile information."""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    company_name = db.Column(db.String(200), nullable=False)
    hr_name = db.Column(db.String(100), nullable=False)
    hr_email = db.Column(db.String(120), nullable=False)
    hr_contact = db.Column(db.String(20), nullable=False)
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    industry = db.Column(db.String(100))
    location = db.Column(db.String(200))
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drives = db.relationship('PlacementDrive', backref='company', lazy=True)
    
    def to_dict(self):
        """Convert company to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_name': self.company_name,
            'hr_name': self.hr_name,
            'hr_email': self.hr_email,
            'hr_contact': self.hr_contact,
            'website': self.website,
            'description': self.description,
            'industry': self.industry,
            'location': self.location,
            'approval_status': self.approval_status,
            'is_blacklisted': self.is_blacklisted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Company {self.company_name}>'
