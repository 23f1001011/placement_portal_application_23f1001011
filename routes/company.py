from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db
from models.user import User
from models.company import Company
from models.drive import PlacementDrive
from models.application import Application
from utils.validators import normalize_graduation_years
from datetime import datetime

company_bp = Blueprint('company', __name__)

def get_current_company():
    """Get current company from JWT identity."""
    try:
        identity = get_jwt_identity()
        if not identity:
            return None
        
        # identity is the user ID as a string from create_access_token
        # We need to get the role from additional_claims
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        user_role = claims.get('role', '')
        
        if user_role != 'company':
            return None
        
        # Get user by ID (identity is the user ID as string)
        user_id = int(identity) if isinstance(identity, str) else identity
        user = User.query.get(user_id)
        if not user:
            return None
        return user.company if user else None
    except Exception as e:
        print(f"Error in get_current_company: {str(e)}")
        return None


@company_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get company profile."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    return jsonify(company.to_dict()), 200


@company_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update company profile."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    data = request.get_json()
    
    if 'company_name' in data:
        company.company_name = data['company_name']
    if 'hr_name' in data:
        company.hr_name = data['hr_name']
    if 'hr_contact' in data:
        company.hr_contact = data['hr_contact']
    if 'website' in data:
        company.website = data['website']
    if 'description' in data:
        company.description = data['description']
    if 'industry' in data:
        company.industry = data['industry']
    if 'location' in data:
        company.location = data['location']
    
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully', 'company': company.to_dict()}), 200


@company_bp.route('/drives', methods=['GET'])
@jwt_required()
def get_drives():
    """Get company's placement drives."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    return jsonify([d.to_dict() for d in drives]), 200


@company_bp.route('/drives', methods=['POST'])
@jwt_required()
def create_drive():
    """Create a new placement drive."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    # Check if company is approved
    if company.approval_status != 'approved':
        return jsonify({'error': 'Company must be approved to create drives'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['job_title', 'job_description', 'eligibility_branch', 
                      'eligibility_cgpa', 'eligibility_year', 'application_deadline']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Parse deadline
    try:
        deadline = datetime.fromisoformat(data['application_deadline'].replace('Z', '+00:00'))
    except:
        return jsonify({'error': 'Invalid deadline format'}), 400

    normalized_years = normalize_graduation_years(data['eligibility_year'])
    if normalized_years is None:
        return jsonify({'error': 'Eligibility year must be comma-separated graduation years like 2026, 2027'}), 400
    
    drive = PlacementDrive(
        company_id=company.id,
        job_title=data['job_title'],
        job_description=data['job_description'],
        eligibility_branch=data['eligibility_branch'],
        eligibility_cgpa=float(data['eligibility_cgpa']),
        eligibility_year=normalized_years,
        application_deadline=deadline,
        job_type=data.get('job_type', 'Full-time'),
        salary_package=data.get('salary_package', ''),
        job_location=data.get('job_location', ''),
        status='pending'  # Requires admin approval
    )
    
    db.session.add(drive)
    db.session.commit()
    
    return jsonify({
        'message': 'Drive created successfully, pending approval',
        'drive': drive.to_dict()
    }), 201


@company_bp.route('/drives/<int:drive_id>', methods=['GET'])
@jwt_required()
def get_drive(drive_id):
    """Get a specific placement drive."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    return jsonify(drive.to_dict()), 200


@company_bp.route('/drives/<int:drive_id>', methods=['PUT'])
@jwt_required()
def update_drive(drive_id):
    """Update a placement drive."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    # Cannot update if already approved
    if drive.status == 'approved':
        return jsonify({'error': 'Cannot update an approved drive'}), 400
    
    data = request.get_json()
    
    if 'job_title' in data:
        drive.job_title = data['job_title']
    if 'job_description' in data:
        drive.job_description = data['job_description']
    if 'eligibility_branch' in data:
        drive.eligibility_branch = data['eligibility_branch']
    if 'eligibility_cgpa' in data:
        drive.eligibility_cgpa = float(data['eligibility_cgpa'])
    if 'eligibility_year' in data:
        normalized_years = normalize_graduation_years(data['eligibility_year'])
        if normalized_years is None:
            return jsonify({'error': 'Eligibility year must be comma-separated graduation years like 2026, 2027'}), 400
        drive.eligibility_year = normalized_years
    if 'application_deadline' in data:
        drive.application_deadline = datetime.fromisoformat(data['application_deadline'].replace('Z', '+00:00'))
    if 'job_type' in data:
        drive.job_type = data['job_type']
    if 'salary_package' in data:
        drive.salary_package = data['salary_package']
    if 'job_location' in data:
        drive.job_location = data['job_location']
    
    db.session.commit()
    
    return jsonify({'message': 'Drive updated successfully', 'drive': drive.to_dict()}), 200


@company_bp.route('/drives/<int:drive_id>/close', methods=['POST'])
@jwt_required()
def close_drive(drive_id):
    """Close a placement drive."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    drive.status = 'closed'
    db.session.commit()
    
    return jsonify({'message': 'Drive closed successfully', 'drive': drive.to_dict()}), 200


@company_bp.route('/applications', methods=['GET'])
@jwt_required()
def get_all_applications():
    """Get all applications for company's drives."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    # Get all applications for all drives of this company
    applications = Application.query.join(PlacementDrive).filter(
        PlacementDrive.company_id == company.id
    ).all()
    
    return jsonify([app.to_dict() for app in applications]), 200


@company_bp.route('/drives/<int:drive_id>/applications', methods=['GET'])
@jwt_required()
def get_applications(drive_id):
    """Get applications for a specific drive."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    applications = Application.query.filter_by(drive_id=drive_id).all()
    return jsonify([app.to_dict() for app in applications]), 200


@company_bp.route('/applications/<int:application_id>/shortlist', methods=['POST'])
@jwt_required()
def shortlist_application(application_id):
    """Shortlist a student application."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    application = Application.query.get(application_id)
    if not application:
        return jsonify({'error': 'Application not found'}), 404
    
    # Verify the application belongs to this company's drive
    if application.drive.company_id != company.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    application.status = 'shortlisted'
    db.session.commit()
    
    return jsonify({'message': 'Student shortlisted', 'application': application.to_dict()}), 200


@company_bp.route('/applications/<int:application_id>/select', methods=['POST'])
@jwt_required()
def select_application(application_id):
    """Select a student (final selection)."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    application = Application.query.get(application_id)
    if not application:
        return jsonify({'error': 'Application not found'}), 404
    
    # Verify the application belongs to this company's drive
    if application.drive.company_id != company.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    application.status = 'selected'
    db.session.commit()
    
    return jsonify({'message': 'Student selected', 'application': application.to_dict()}), 200


@company_bp.route('/applications/<int:application_id>/reject', methods=['POST'])
@jwt_required()
def reject_application(application_id):
    """Reject a student application."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    application = Application.query.get(application_id)
    if not application:
        return jsonify({'error': 'Application not found'}), 404
    
    # Verify the application belongs to this company's drive
    if application.drive.company_id != company.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    application.status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': 'Application rejected', 'application': application.to_dict()}), 200


@company_bp.route('/applications/<int:application_id>/schedule', methods=['POST'])
@jwt_required()
def schedule_interview(application_id):
    """Schedule interview for a student."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    application = Application.query.get(application_id)
    if not application:
        return jsonify({'error': 'Application not found'}), 404
    
    # Verify the application belongs to this company's drive
    if application.drive.company_id != company.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if 'interview_date' in data:
        application.interview_date = datetime.fromisoformat(data['interview_date'].replace('Z', '+00:00'))
    if 'interview_location' in data:
        application.interview_location = data['interview_location']
    if 'notes' in data:
        application.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({'message': 'Interview scheduled', 'application': application.to_dict()}), 200


@company_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get company dashboard statistics."""
    company = get_current_company()
    if not company:
        return jsonify({'error': 'Company profile not found'}), 404
    
    # Get company statistics
    total_drives = PlacementDrive.query.filter_by(company_id=company.id).count()
    approved_drives = PlacementDrive.query.filter_by(company_id=company.id, status='approved').count()
    
    # Get application counts per drive
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    drive_stats = []
    for drive in drives:
        applications = Application.query.filter_by(drive_id=drive.id).all()
        drive_stats.append({
            'drive_id': drive.id,
            'job_title': drive.job_title,
            'total_applications': len(applications),
            'shortlisted': len([a for a in applications if a.status == 'shortlisted']),
            'selected': len([a for a in applications if a.status == 'selected'])
        })
    
    return jsonify({
        'company': company.to_dict(),
        'total_drives': total_drives,
        'approved_drives': approved_drives,
        'drive_stats': drive_stats
    }), 200
