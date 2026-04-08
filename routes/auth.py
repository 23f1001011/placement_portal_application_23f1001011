from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import db
from models.user import User
from models.company import Company
from models.student import Student
from utils.cache import invalidate_prefix

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (student or company)."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Validate role
    if data['role'] not in ['student', 'company']:
        return jsonify({'error': 'Invalid role. Must be student or company'}), 400
    
    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        role=data['role']
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Create profile based on role
    if data['role'] == 'company':
        company = Company(
            user_id=user.id,
            company_name=data.get('company_name', data['username']),
            hr_name=data.get('hr_name', ''),
            hr_email=data['email'],
            hr_contact=data.get('hr_contact', '')
        )
        db.session.add(company)
    elif data['role'] == 'student':
        student = Student(
            user_id=user.id,
            full_name=data.get('full_name', data['username']),
            roll_number=data.get('roll_number', ''),
            email=data['email'],
            branch=data.get('branch', ''),
            year=data.get('year', 2024),
            cgpa=data.get('cgpa', 0.0)
        )
        db.session.add(student)
    
    db.session.commit()
    
    # Invalidate admin dashboard cache to reflect new user
    invalidate_prefix('admin_')
    
    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token."""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 401
    
    if user.is_blacklisted:
        return jsonify({'error': 'Account is blacklisted'}), 401
    
    # Create tokens - encode role in JWT additional claims
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role}
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={'role': user.role}
    )
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information."""
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = user.to_dict()
    
    # Add role-specific data
    if user.role == 'company' and user.company:
        user_data['company'] = user.company.to_dict()
    elif user.role == 'student' and user.student:
        user_data['student'] = user.student.to_dict()
    
    return jsonify(user_data), 200
