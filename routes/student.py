from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db
from models.user import User
from models.student import Student
from models.drive import PlacementDrive
from models.application import Application
from datetime import datetime, timedelta
from utils.cache import cache_get, cache_set, invalidate_cache, invalidate_prefix
from utils.validators import normalize_graduation_years

student_bp = Blueprint('student', __name__)

def get_current_student():
    """Get current student from JWT identity."""
    try:
        identity = get_jwt_identity()
        if not identity:
            return None
        
        # identity is the user ID as a string from create_access_token
        # We need to get the role from additional_claims
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        user_role = claims.get('role', '')
        
        if user_role != 'student':
            return None
        
        # Get user by ID (identity is the user ID as string)
        user_id = int(identity) if isinstance(identity, str) else identity
        user = User.query.get(user_id)
        if not user:
            return None
        return user.student if user else None
    except Exception as e:
        print(f"Error in get_current_student: {str(e)}")
        return None


@student_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get student profile."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        return jsonify(student.to_dict()), 200
    except Exception as e:
        print(f"Error in get_profile: {str(e)}")
        return jsonify({'error': 'Failed to fetch profile', 'details': str(e)}), 500


@student_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update student profile."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        data = request.get_json()
        
        if 'full_name' in data:
            student.full_name = data['full_name']
        if 'phone' in data:
            student.phone = data['phone']
        if 'branch' in data:
            student.branch = data['branch']
        if 'year' in data:
            student.year = data['year']
        if 'cgpa' in data:
            student.cgpa = float(data['cgpa'])
        if 'resume_url' in data:
            student.resume_url = data['resume_url']
        if 'date_of_birth' in data:
            student.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        if 'gender' in data:
            student.gender = data['gender']
        if 'address' in data:
            student.address = data['address']
        if 'skills' in data:
            student.skills = data['skills']
        
        db.session.commit()
        
        # Invalidate admin dashboard cache
        invalidate_prefix('admin_')
        
        return jsonify({'message': 'Profile updated successfully', 'student': student.to_dict()}), 200
    except Exception as e:
        print(f"Error in update_profile: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile', 'details': str(e)}), 500


@student_bp.route('/drives', methods=['GET'])
@jwt_required()
def get_drives():
    """Get available placement drives for the student."""
    try:
        # Try to get from cache first
        cache_key = 'available_drives'
        cached_drives = cache_get(cache_key)
        if cached_drives:
            return jsonify(cached_drives), 200
        
        # Get approved drives with future deadlines
        drives = PlacementDrive.query.filter(
            PlacementDrive.status == 'approved',
            PlacementDrive.application_deadline > datetime.utcnow()
        ).all()
        
        drives_data = []
        student = get_current_student()
        
        for drive in drives:
            try:
                drive_dict = drive.to_dict()
                
                # Check if student has already applied
                if student:
                    application = Application.query.filter_by(
                        student_id=student.id,
                        drive_id=drive.id
                    ).first()
                    drive_dict['has_applied'] = application is not None
                    drive_dict['application_status'] = application.status if application else None
                else:
                    drive_dict['has_applied'] = False
                    drive_dict['application_status'] = None
                
                drives_data.append(drive_dict)
            except Exception as e:
                print(f"Error processing drive {drive.id}: {str(e)}")
                continue
        
        # Cache for 5 minutes
        cache_set(cache_key, drives_data, timeout=300)
        
        return jsonify(drives_data), 200
    except Exception as e:
        print(f"Error in get_drives: {str(e)}")
        return jsonify({'error': 'Failed to fetch drives', 'details': str(e)}), 500


@student_bp.route('/drives/<int:drive_id>', methods=['GET'])
@jwt_required()
def get_drive_details(drive_id):
    """Get details of a specific placement drive."""
    try:
        drive = PlacementDrive.query.get(drive_id)
        if not drive:
            return jsonify({'error': 'Drive not found'}), 404
        
        if drive.status != 'approved':
            return jsonify({'error': 'Drive is not available'}), 400
        
        drive_dict = drive.to_dict()
        
        student = get_current_student()
        if student:
            application = Application.query.filter_by(
                student_id=student.id,
                drive_id=drive_id
            ).first()
            drive_dict['has_applied'] = application is not None
            drive_dict['application_status'] = application.status if application else None
        
        return jsonify(drive_dict), 200
    except Exception as e:
        print(f"Error in get_drive_details: {str(e)}")
        return jsonify({'error': 'Failed to fetch drive details', 'details': str(e)}), 500


@student_bp.route('/drives/<int:drive_id>/apply', methods=['POST'])
@jwt_required()
def apply_for_drive(drive_id):
    """Apply for a placement drive."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Check if blacklisted
        if student.is_blacklisted:
            return jsonify({'error': 'You are blacklisted and cannot apply'}), 403
        
        drive = PlacementDrive.query.get(drive_id)
        if not drive:
            return jsonify({'error': 'Drive not found'}), 404
        
        print(f"DEBUG: Student applying - ID: {student.id}, Branch: {student.branch}, Year: {student.year}, CGPA: {student.cgpa}")
        print(f"DEBUG: Drive - ID: {drive.id}, Status: {drive.status}, Deadline: {drive.application_deadline}")
        print(f"DEBUG: Drive eligibility - Branch: {drive.eligibility_branch}, Year: {drive.eligibility_year}, CGPA: {drive.eligibility_cgpa}")
        
        if drive.status != 'approved':
            print(f"DEBUG: Drive status check failed - status: {drive.status}")
            return jsonify({'error': 'Drive is not accepting applications'}), 400
        
        # Check deadline
        if drive.application_deadline < datetime.utcnow():
            print(f"DEBUG: Deadline check failed - deadline: {drive.application_deadline}, now: {datetime.utcnow()}")
            return jsonify({'error': 'Application deadline has passed'}), 400
        
        # Check eligibility
        eligible_branches = [b.strip().lower() for b in drive.eligibility_branch.split(',')]
        normalized_years = normalize_graduation_years(drive.eligibility_year)
        if normalized_years is None:
            print(f"DEBUG: Invalid drive eligibility year format: {drive.eligibility_year}")
            return jsonify({'error': 'Drive eligibility year is invalid'}), 400
        eligible_years = normalized_years.split(',')

        print(f"DEBUG: Parsed eligible branches: {eligible_branches}")
        print(f"DEBUG: Parsed eligible years: {eligible_years}")
        print(f"DEBUG: Student branch: '{student.branch.lower()}' in eligible: {student.branch.lower() in eligible_branches}")
        print(f"DEBUG: Student year: '{str(student.year)}' in eligible: {str(student.year) in eligible_years}")
        print(f"DEBUG: Student CGPA: {student.cgpa} >= required: {drive.eligibility_cgpa}")

        if student.branch.lower() not in eligible_branches:
            print(f"DEBUG: Branch eligibility failed")
            return jsonify({'error': 'You are not eligible for this drive (branch)'}), 400

        if str(student.year) not in eligible_years:
            print(f"DEBUG: Year eligibility failed")
            return jsonify({'error': 'You are not eligible for this drive (year)'}), 400
        
        if student.cgpa < drive.eligibility_cgpa:
            print(f"DEBUG: CGPA eligibility failed")
            return jsonify({'error': 'Your CGPA is below the eligibility criteria'}), 400
        
        # Check if already applied
        existing_application = Application.query.filter_by(
            student_id=student.id,
            drive_id=drive_id
        ).first()
        
        if existing_application:
            print(f"DEBUG: Already applied check failed")
            return jsonify({'error': 'You have already applied for this drive'}), 400
        
        print(f"DEBUG: All validations passed, creating application")
        
        # Create application
        application = Application(
            student_id=student.id,
            drive_id=drive_id,
            status='applied'
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Invalidate cache
        invalidate_cache('available_drives')
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application': application.to_dict()
        }), 201
    except Exception as e:
        print(f"Error in apply_for_drive: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to apply for drive', 'details': str(e)}), 500


@student_bp.route('/applications', methods=['GET'])
@jwt_required()
def get_applications():
    """Get student's applications."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        applications = Application.query.filter_by(student_id=student.id).all()
        return jsonify([app.to_dict() for app in applications]), 200
    except Exception as e:
        print(f"Error in get_applications: {str(e)}")
        return jsonify({'error': 'Failed to fetch applications', 'details': str(e)}), 500


@student_bp.route('/applications/<int:application_id>', methods=['GET'])
@jwt_required()
def get_application(application_id):
    """Get details of a specific application."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        application = Application.query.filter_by(
            id=application_id,
            student_id=student.id
        ).first()
        
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        return jsonify(application.to_dict()), 200
    except Exception as e:
        print(f"Error in get_application: {str(e)}")
        return jsonify({'error': 'Failed to fetch application', 'details': str(e)}), 500


@student_bp.route('/applications/<int:application_id>/withdraw', methods=['POST'])
@jwt_required()
def withdraw_application(application_id):
    """Withdraw an application."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        application = Application.query.filter_by(
            id=application_id,
            student_id=student.id
        ).first()
        
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        if application.status in ['selected', 'rejected']:
            return jsonify({'error': 'Cannot withdraw a processed application'}), 400
        
        application.is_withdrawn = True
        application.status = 'withdrawn'
        db.session.commit()
        
        return jsonify({'message': 'Application withdrawn', 'application': application.to_dict()}), 200
    except Exception as e:
        print(f"Error in withdraw_application: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to withdraw application', 'details': str(e)}), 500


@student_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get student dashboard."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Get application statistics
        applications = Application.query.filter_by(student_id=student.id).all()
        
        total_applications = len(applications)
        pending_applications = len([a for a in applications if a.status == 'applied'])
        shortlisted = len([a for a in applications if a.status == 'shortlisted'])
        selected = len([a for a in applications if a.status == 'selected'])
        rejected = len([a for a in applications if a.status == 'rejected'])
        
        # Get upcoming deadlines (drives with future deadlines)
        upcoming_drives = PlacementDrive.query.filter(
            PlacementDrive.status == 'approved',
            PlacementDrive.application_deadline > datetime.utcnow(),
            PlacementDrive.application_deadline < datetime.utcnow() + timedelta(days=7)
        ).limit(5).all()
        
        return jsonify({
            'student': student.to_dict(),
            'statistics': {
                'total_applications': total_applications,
                'pending': pending_applications,
                'shortlisted': shortlisted,
                'selected': selected,
                'rejected': rejected
            },
            'upcoming_deadlines': [d.to_dict() for d in upcoming_drives]
        }), 200
    except Exception as e:
        print(f"Error in get_dashboard: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard', 'details': str(e)}), 500


@student_bp.route('/search', methods=['GET'])
@jwt_required()
def search_drives():
    """Search for placement drives."""
    try:
        query = request.args.get('q', '')
        branch = request.args.get('branch')
        job_type = request.args.get('job_type')
        
        drives_query = PlacementDrive.query.filter(
            PlacementDrive.status == 'approved',
            PlacementDrive.application_deadline > datetime.utcnow()
        )
        
        if query:
            drives_query = drives_query.filter(
                (PlacementDrive.job_title.ilike(f'%{query}%')) |
                (PlacementDrive.job_description.ilike(f'%{query}%'))
            )
        
        if branch:
            drives_query = drives_query.filter(
                PlacementDrive.eligibility_branch.ilike(f'%{branch}%')
            )
        
        if job_type:
            drives_query = drives_query.filter_by(job_type=job_type)
        
        drives = drives_query.all()
        return jsonify([d.to_dict() for d in drives]), 200
    except Exception as e:
        print(f"Error in search_drives: {str(e)}")
        return jsonify({'error': 'Failed to search drives', 'details': str(e)}), 500


@student_bp.route('/export-csv', methods=['POST'])
@jwt_required()
def export_applications_csv():
    """Trigger CSV export for student's application history."""
    try:
        student = get_current_student()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Import the Celery instance and send task by name
        from celery_tasks.celery_app import celery
        result = celery.send_task('export_applications_csv', args=[student.id])
        print(f"✅ CSV export task sent for student {student.id}. Task ID: {result.id}")
        
        return jsonify({
            'message': 'CSV export initiated. You will receive an email shortly.',
            'task_id': result.id
        }), 202
    except Exception as e:
        import traceback
        print(f"❌ Error in export_applications_csv: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to initiate CSV export', 'details': str(e)}), 500
