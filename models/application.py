from datetime import datetime
from models import db

class Application(db.Model):
    """Application model for student applications to placement drives."""
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='applied')  # applied, shortlisted, selected, rejected
    interview_date = db.Column(db.DateTime)
    interview_location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    is_withdrawn = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique application per student per drive
    __table_args__ = (
        db.UniqueConstraint('student_id', 'drive_id', name='unique_student_drive'),
    )
    
    def to_dict(self):
        """Convert application to dictionary."""
        # Safely get student info with None checks
        student_name = None
        roll_number = None
        if self.student:
            student_name = self.student.full_name
            roll_number = self.student.roll_number
        
        # Safely get drive info with None checks
        drive_title = None
        company_name = None
        if self.drive:
            drive_title = self.drive.job_title
            if self.drive.company:
                company_name = self.drive.company.company_name
        
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': student_name,
            'roll_number': roll_number,
            'drive_id': self.drive_id,
            'drive_title': drive_title,
            'company_name': company_name,
            'application_date': self.application_date.isoformat() if self.application_date else None,
            'status': self.status,
            'interview_date': self.interview_date.isoformat() if self.interview_date else None,
            'interview_location': self.interview_location,
            'notes': self.notes,
            'is_withdrawn': self.is_withdrawn
        }
    
    def __repr__(self):
        return f'<Application {self.student_id} - {self.drive_id} - {self.status}>'
