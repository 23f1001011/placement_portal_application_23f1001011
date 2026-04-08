import re
from datetime import datetime

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone number format."""
    pattern = r'^[0-9]{10,15}$'
    return re.match(pattern, phone) is not None


def validate_roll_number(roll_number):
    """Validate roll number format."""
    # Basic validation - alphanumeric, 5-20 characters
    pattern = r'^[a-zA-Z0-9]{5,20}$'
    return re.match(pattern, roll_number) is not None


def validate_username(username):
    """Validate username format."""
    # Alphanumeric and underscore, 3-30 characters
    pattern = r'^[a-zA-Z0-9_]{3,30}$'
    return re.match(pattern, username) is not None


def validate_password(password):
    """Validate password strength."""
    # At least 8 characters
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    return True, None


def validate_cgpa(cgpa):
    """Validate CGPA."""
    try:
        cgpa_value = float(cgpa)
        return 0 <= cgpa_value <= 10
    except:
        return False


def validate_year(year):
    """Validate year."""
    try:
        year_value = int(year)
        current_year = datetime.now().year
        return 2000 <= year_value <= current_year + 5
    except:
        return False


def validate_date_format(date_string):
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except:
        return False


def validate_datetime_format(datetime_string):
    """Validate datetime format (ISO format)."""
    try:
        datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return True
    except:
        return False


def normalize_graduation_years(year_string):
    """Normalize a comma-separated list of graduation years to clean 4-digit values."""
    years = [y.strip() for y in year_string.split(',') if y.strip()]
    if not years:
        return None

    normalized = []
    for y in years:
        if not y.isdigit() or len(y) != 4:
            return None
        normalized.append(y)

    return ','.join(normalized)


def validate_file_extension(filename, allowed_extensions):
    """Validate file extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions
