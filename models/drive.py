from datetime import datetime
from models import db

class PlacementDrive(db.Model):
    """PlacementDrive model for placement drive/job posting information."""
    __tablename__ = 'placement_drives'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility_branch = db.Column(db.String(100), nullable=False)  # Eligible branches
    eligibility_cgpa = db.Column(db.Float, nullable=False)  # Minimum CGPA
    eligibility_year = db.Column(db.String(50), nullable=False)  # Eligible graduation years (e.g., "2026,2027")
    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, closed
    job_type = db.Column(db.String(50))  # Full-time, Internship, etc.
    salary_package = db.Column(db.String(100))  # Salary details
    job_location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='drive', lazy=True)
    
    def to_dict(self):
        """Convert drive to dictionary."""
        # Safely get company_name with None check
        company_name = None
        if self.company:
            company_name = self.company.company_name
        
        # Safely get application count
        application_count = 0
        if self.applications:
            application_count = len(self.applications)
        
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': company_name,
            'job_title': self.job_title,
            'job_description': self.job_description,
            'eligibility_branch': self.eligibility_branch,
            'eligibility_cgpa': self.eligibility_cgpa,
            'eligibility_year': self.eligibility_year,
            'application_deadline': self.application_deadline.isoformat() if self.application_deadline else None,
            'status': self.status,
            'job_type': self.job_type,
            'salary_package': self.salary_package,
            'job_location': self.job_location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'application_count': application_count
        }
    
    def __repr__(self):
        return f'<PlacementDrive {self.job_title} - {self.company_id}>'
