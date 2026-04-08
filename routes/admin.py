from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db
from models.user import User
from models.company import Company
from models.student import Student
from models.drive import PlacementDrive
from models.application import Application
from utils.cache import invalidate_prefix, invalidate_cache

admin_bp = Blueprint('admin', __name__)

def admin_required():
    """Decorator to check if user is admin."""
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    return None


@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get admin dashboard statistics."""
    # Check admin access
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    # User statistics
    total_users = User.query.count()
    total_admins = User.query.filter_by(role='admin').count()
    total_companies_users = User.query.filter_by(role='company').count()
    total_students_users = User.query.filter_by(role='student').count()
    active_users = User.query.filter_by(is_active=True).count()
    blacklisted_users = User.query.filter_by(is_blacklisted=True).count()
    
    # Entity statistics
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()
    
    # Pending approvals
    pending_companies = Company.query.filter_by(approval_status='pending').count()
    pending_drives = PlacementDrive.query.filter_by(status='pending').count()
    
    # Recent activity
    recent_applications = Application.query.order_by(Application.created_at.desc()).limit(10).all()
    
    return jsonify({
        'total_users': total_users,
        'total_admins': total_admins,
        'total_companies_users': total_companies_users,
        'total_students_users': total_students_users,
        'active_users': active_users,
        'blacklisted_users': blacklisted_users,
        'total_students': total_students,
        'total_companies': total_companies,
        'total_drives': total_drives,
        'total_applications': total_applications,
        'pending_companies': pending_companies,
        'pending_drives': pending_drives,
        'recent_applications': [app.to_dict() for app in recent_applications]
    }), 200


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users with optional filtering."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    # Get query parameters
    role = request.args.get('role')
    is_active = request.args.get('is_active')
    is_blacklisted = request.args.get('is_blacklisted')
    search = request.args.get('search')
    
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')
    
    if is_blacklisted is not None:
        query = query.filter_by(is_blacklisted=is_blacklisted.lower() == 'true')
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    users = query.order_by(User.created_at.desc()).all()
    
    # Include additional info based on role
    users_data = []
    for user in users:
        user_dict = user.to_dict()
        if user.role == 'student' and user.student:
            user_dict['student_info'] = {
                'full_name': user.student.full_name,
                'roll_number': user.student.roll_number,
                'branch': user.student.branch,
                'year': user.student.year
            }
        elif user.role == 'company' and user.company:
            user_dict['company_info'] = {
                'company_name': user.company.company_name,
                'approval_status': user.company.approval_status
            }
        users_data.append(user_dict)
    
    return jsonify(users_data), 200


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@jwt_required()
def toggle_user_status(user_id):
    """Toggle user active status."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent deactivating own account
    identity = get_jwt_identity()
    current_user_id = int(identity) if isinstance(identity, str) else identity
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    # Invalidate cache
    invalidate_prefix('admin_')
    
    return jsonify({
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/blacklist', methods=['POST'])
@jwt_required()
def blacklist_user(user_id):
    """Blacklist or unblacklist a user."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_blacklisted = not user.is_blacklisted
    
    # Also blacklist the related entity (student or company)
    if user.role == 'student' and user.student:
        user.student.is_blacklisted = user.is_blacklisted
    elif user.role == 'company' and user.company:
        user.company.is_blacklisted = user.is_blacklisted
    
    db.session.commit()
    
    # Invalidate cache
    invalidate_prefix('admin_')
    
    return jsonify({
        'message': f'User {"blacklisted" if user.is_blacklisted else "unblacklisted"} successfully',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete a user and their related data."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent deleting own account
    identity = get_jwt_identity()
    current_user_id = int(identity) if isinstance(identity, str) else identity
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Delete related data based on role
    if user.role == 'student' and user.student:
        # Delete student's applications first
        Application.query.filter_by(student_id=user.student.id).delete()
        db.session.delete(user.student)
    elif user.role == 'company' and user.company:
        # Delete company's drives and applications
        drives = PlacementDrive.query.filter_by(company_id=user.company.id).all()
        for drive in drives:
            Application.query.filter_by(drive_id=drive.id).delete()
        PlacementDrive.query.filter_by(company_id=user.company.id).delete()
        db.session.delete(user.company)
    
    db.session.delete(user)
    db.session.commit()
    
    # Invalidate cache
    invalidate_prefix('admin_')
    
    return jsonify({'message': 'User deleted successfully'}), 200


@admin_bp.route('/companies', methods=['GET'])
@jwt_required()
def get_companies():
    """Get all companies with optional filtering."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    # Get query parameters
    status = request.args.get('status')
    search = request.args.get('search')
    
    query = Company.query
    
    if status:
        query = query.filter_by(approval_status=status)
    
    if search:
        query = query.filter(
            (Company.company_name.ilike(f'%{search}%')) |
            (Company.hr_email.ilike(f'%{search}%'))
        )
    
    companies = query.all()
    return jsonify([c.to_dict() for c in companies]), 200


@admin_bp.route('/companies/<int:company_id>/approve', methods=['POST'])
@jwt_required()
def approve_company(company_id):
    """Approve a company registration."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.approval_status = 'approved'
    db.session.commit()
    
    return jsonify({'message': 'Company approved successfully', 'company': company.to_dict()}), 200


@admin_bp.route('/companies/<int:company_id>/reject', methods=['POST'])
@jwt_required()
def reject_company(company_id):
    """Reject a company registration."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.approval_status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': 'Company rejected', 'company': company.to_dict()}), 200


@admin_bp.route('/companies/<int:company_id>/blacklist', methods=['POST'])
@jwt_required()
def blacklist_company(company_id):
    """Blacklist a company."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    company.is_blacklisted = True
    company.user.is_blacklisted = True
    db.session.commit()
    
    return jsonify({'message': 'Company blacklisted', 'company': company.to_dict()}), 200


@admin_bp.route('/drives', methods=['GET'])
@jwt_required()
def get_drives():
    """Get all placement drives."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    status = request.args.get('status')
    query = PlacementDrive.query
    
    if status:
        query = query.filter_by(status=status)
    
    drives = query.all()
    return jsonify([d.to_dict() for d in drives]), 200


@admin_bp.route('/drives/<int:drive_id>/approve', methods=['POST'])
@jwt_required()
def approve_drive(drive_id):
    """Approve a placement drive."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    drive.status = 'approved'
    db.session.commit()
    
    # Invalidate cache
    invalidate_cache('available_drives')
    
    return jsonify({'message': 'Drive approved successfully', 'drive': drive.to_dict()}), 200


@admin_bp.route('/drives/<int:drive_id>/reject', methods=['POST'])
@jwt_required()
def reject_drive(drive_id):
    """Reject a placement drive."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    
    drive.status = 'rejected'
    db.session.commit()
    
    # Invalidate cache
    invalidate_cache('available_drives')
    
    return jsonify({'message': 'Drive rejected', 'drive': drive.to_dict()}), 200


@admin_bp.route('/students', methods=['GET'])
@jwt_required()
def get_students():
    """Get all students with optional filtering."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    search = request.args.get('search')
    branch = request.args.get('branch')
    year = request.args.get('year')
    
    query = Student.query
    
    if search:
        query = query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (Student.roll_number.ilike(f'%{search}%')) |
            (Student.email.ilike(f'%{search}%'))
        )
    
    if branch:
        query = query.filter_by(branch=branch)
    
    if year:
        query = query.filter_by(year=int(year))
    
    students = query.all()
    return jsonify([s.to_dict() for s in students]), 200


@admin_bp.route('/students/<int:student_id>/blacklist', methods=['POST'])
@jwt_required()
def blacklist_student(student_id):
    """Blacklist a student."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.is_blacklisted = True
    student.user.is_blacklisted = True
    db.session.commit()
    
    return jsonify({'message': 'Student blacklisted', 'student': student.to_dict()}), 200


@admin_bp.route('/applications', methods=['GET'])
@jwt_required()
def get_all_applications():
    """Get all applications."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    applications = Application.query.all()
    return jsonify([app.to_dict() for app in applications]), 200


@admin_bp.route('/reports/statistics', methods=['GET'])
@jwt_required()
def get_statistics():
    """Get placement statistics."""
    auth_error = admin_required()
    if auth_error:
        return auth_error
    
    # Get statistics
    total_drives = PlacementDrive.query.filter_by(status='approved').count()
    total_applications = Application.query.count()
    selected_students = Application.query.filter_by(status='selected').count()
    shortlisted_students = Application.query.filter_by(status='shortlisted').count()
    
    # Applications by status
    status_counts = db.session.query(
        Application.status,
        db.func.count(Application.id)
    ).group_by(Application.status).all()
    
    applications_by_status = {status: count for status, count in status_counts}
    
    # Company statistics
    company_stats = []
    companies = Company.query.filter_by(approval_status='approved').all()
    for company in companies:
        drives = PlacementDrive.query.filter_by(company_id=company.id).all()
        drive_count = len(drives)
        applications = Application.query.join(PlacementDrive).filter(
            PlacementDrive.company_id == company.id
        ).count()
        company_stats.append({
            'company_name': company.company_name,
            'drive_count': drive_count,
            'application_count': applications
        })
    
    return jsonify({
        'total_drives': total_drives,
        'total_applications': total_applications,
        'selected_students': selected_students,
        'shortlisted_students': shortlisted_students,
        'applications_by_status': applications_by_status,
        'company_stats': company_stats
    }), 200
