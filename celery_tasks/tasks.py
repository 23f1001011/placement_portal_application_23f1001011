from celery_tasks.celery_app import celery
from flask_mail import Message
from datetime import datetime, timedelta
import csv
import io
import logging
import socket

logger = logging.getLogger(__name__)

def _mail_debug(current_app):
    cfg = {
        'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
        'MAIL_PORT': current_app.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
        'MAIL_USE_SSL': current_app.config.get('MAIL_USE_SSL'),
        'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
    }
    logger.info(f"📧 Mail config: {cfg}")
    if not cfg['MAIL_SERVER'] or not cfg['MAIL_USERNAME'] or not current_app.config.get('MAIL_PASSWORD'):
        logger.error("❌ Mail configuration incomplete (server/user/password)")
        return False

    try:
        socket.getaddrinfo(cfg['MAIL_SERVER'], cfg['MAIL_PORT'])
    except socket.gaierror as e:
        logger.error("❌ Mail server DNS lookup failed for %s:%s - %s",
                     cfg['MAIL_SERVER'], cfg['MAIL_PORT'], e)
        logger.error("Please set MAIL_SERVER correctly in .env (e.g., smtp.gmail.com / smtp.office365.com)")
        return False

    return True

@celery.task(bind=True, name='send_daily_reminders')
def send_daily_reminders(self):
    """Send daily reminders to students about upcoming application deadlines."""
    from flask import current_app
    from models import db
    from models.student import Student
    from models.drive import PlacementDrive
    from models.application import Application

    mail = current_app.extensions.get('mail')
    if not mail:
        logger.warning("Mail extension not available")
        return "Mail not configured"
    
    # Get drives with deadlines in the next 3 days
    upcoming_drives = PlacementDrive.query.filter(
        PlacementDrive.status == 'approved',
        PlacementDrive.application_deadline > datetime.utcnow(),
        PlacementDrive.application_deadline < datetime.utcnow() + timedelta(days=3)
    ).all()
    
    sent_count = 0
    
    for drive in upcoming_drives:
        # Get eligible students who haven't applied yet
        eligible_branches = [b.strip().lower() for b in drive.eligibility_branch.split(',')]
        eligible_years = [y.strip() for y in drive.eligibility_year.split(',')]
        
        # Safe int conversion
        valid_years = []
        for y in eligible_years:
            try:
                valid_years.append(int(y))
            except ValueError:
                continue
        
        students = Student.query.filter(
            Student.branch.in_(eligible_branches),
            Student.year.in_(valid_years),
            Student.cgpa >= drive.eligibility_cgpa,
            Student.is_blacklisted == False
        ).all()
        
        for student in students:
            # Check if already applied
            existing_app = Application.query.filter_by(
                student_id=student.id,
                drive_id=drive.id
            ).first()
            
            if not existing_app and student.user and student.user.email:
                try:
                    company_name = drive.company.company_name if drive.company else "Unknown Company"
                    # Send email reminder
                    msg = Message(
                        subject=f"Reminder: {drive.job_title} - Deadline Approaching",
                        recipients=[student.user.email],
                        body=f"""
Dear {student.full_name},

This is a reminder that the application deadline for {drive.job_title} at {company_name} is approaching.

Deadline: {drive.application_deadline.strftime('%Y-%m-%d %H:%M:%S')}

Don't miss this opportunity!

Best regards,
Placement Cell
"""
                    )
                    mail.send(msg)
                    sent_count += 1
                except Exception as e:
                    logging.error(f"Error sending email to {student.user.email}: {e}")
    
    return f"Sent {sent_count} reminder emails"


@celery.task(bind=True, name='generate_monthly_report')
def generate_monthly_report(self):
    """Generate monthly activity report and send to admin."""
    from flask import current_app
    mail = current_app.extensions['mail']
    
    from models import db
    from models.user import User
    from models.drive import PlacementDrive
    from models.application import Application
    
    # Get previous month's data - FIRST DAY of PREVIOUS month to LAST DAY
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    # Last day of previous month
    if today.month == 1:
        prev_month_first = datetime(today.year - 1, 12, 1)
    else:
        prev_month_first = datetime(today.year, today.month - 1, 1)
    prev_month_end = (today.replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
    last_month = prev_month_first
    
    # Get statistics
    total_drives = PlacementDrive.query.filter(
        PlacementDrive.created_at >= prev_month_first,
        PlacementDrive.created_at <= prev_month_end
    ).count()
    
    total_applications = Application.query.filter(
        Application.application_date >= prev_month_first,
        Application.application_date <= prev_month_end
    ).count()
    
    selected_students = Application.query.filter(
        Application.status == 'selected',
        Application.application_date >= prev_month_first,
        Application.application_date <= prev_month_end
    ).count()
    
    # Generate HTML report
    html_report = f"""
    <html>
    <head>
        <title>Monthly Placement Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .stats {{ margin: 20px 0; }}
            .stat-box {{ 
                display: inline-block; 
                padding: 15px 25px; 
                margin: 10px; 
                background: #f0f0f0; 
                border-radius: 5px;
            }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
        <h1>Monthly Placement Activity Report</h1>
        <p>Period: {last_month.strftime('%B %Y')}</p>
        
        <div class="stats">
            <div class="stat-box">
                <h3>{total_drives}</h3>
                <p>Total Drives</p>
            </div>
            <div class="stat-box">
                <h3>{total_applications}</h3>
                <p>Total Applications</p>
            </div>
            <div class="stat-box">
                <h3>{selected_students}</h3>
                <p>Students Selected</p>
            </div>
        </div>
        
        <h2>Placement Drives This Month</h2>
        <table>
            <tr>
                <th>Company</th>
                <th>Job Title</th>
                <th>Status</th>
                <th>Applications</th>
            </tr>
    """
    
    # Add drive details
    drives = PlacementDrive.query.filter(
        PlacementDrive.created_at >= prev_month_first,
        PlacementDrive.created_at <= prev_month_end
    ).all()
    
    for drive in drives:
        app_count = Application.query.filter_by(drive_id=drive.id).count()
        html_report += f"""
            <tr>
                <td>{drive.company.company_name}</td>
                <td>{drive.job_title}</td>
                <td>{drive.status}</td>
                <td>{app_count}</td>
            </tr>
        """
    
    html_report += """
        </table>
    </body>
    </html>
    """
    
    # Send to admin
    admin = User.query.filter_by(role='admin').first()
    if admin and admin.email:
        try:
            msg = Message(
                subject=f"Monthly Placement Report - {last_month.strftime('%B %Y')}",
                recipients=[admin.email],
                html=html_report
            )
            mail.send(msg)
            return "Monthly report sent successfully"
        except Exception as e:
            return f"Error sending report: {str(e)}"
    
    return "No admin email found"


@celery.task(bind=True, name='export_applications_csv')
def export_applications_csv(self, student_id):
    """Export student's application history as CSV."""
    from flask import current_app
    import logging
    logger = logging.getLogger(__name__)
    
    if not _mail_debug(current_app):
        return "Mail configuration incomplete"
    
    mail = current_app.extensions.get('mail')
    if not mail:
        logger.error("❌ Mail extension not configured")
        return "Mail not configured"
    
    from models import db
    from models.student import Student
    from models.application import Application
    
    student = Student.query.get(student_id)
    if not student:
        return "Student not found"
    
    # Get all applications
    applications = Application.query.filter_by(student_id=student_id).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Application ID',
        'Company Name',
        'Drive Title',
        'Job Location',
        'Application Date',
        'Status',
        'Interview Date',
        'Interview Location'
    ])
    
    # Write data
    for app in applications:
        writer.writerow([
            app.id,
            app.drive.company.company_name if app.drive and app.drive.company else '',
            app.drive.job_title if app.drive else '',
            app.drive.job_location if app.drive else '',
            app.application_date.strftime('%Y-%m-%d %H:%M:%S') if app.application_date else '',
            app.status,
            app.interview_date.strftime('%Y-%m-%d %H:%M:%S') if app.interview_date else '',
            app.interview_location or ''
        ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Send email with CSV attachment
    if student.user and student.user.email:
        logger.info(f"📧 Preparing email for {student.user.email}")
        logger.info(f"📧 Mail server: {current_app.config.get('MAIL_SERVER')}")
        logger.info(f"📧 Mail username: {current_app.config.get('MAIL_USERNAME')}")
        logger.info(f"📧 Mail port: {current_app.config.get('MAIL_PORT')}")
        logger.info(f"📧 Mail TLS: {current_app.config.get('MAIL_USE_TLS')}")
        
        msg = Message(
            subject="Your Placement Application History",
            recipients=[student.user.email],
            body=f"""
Dear {student.full_name},

Please find attached your placement application history (CSV format).

Applications: {len(applications)}

Best regards,
Placement Cell
"""
        )
        
        # Attach CSV
        msg.attach(
            filename=f"application_history_{student.roll_number}.csv",
            content_type='text/csv',
            data=csv_content.encode('utf-8')
        )
        
        try:
            mail.send(msg)
            logger.info(f"✅ CSV email sent successfully to {student.user.email}")
            return "CSV exported and sent successfully"
        except Exception as e:
            logger.error(f"❌ Email FAILED to {student.user.email}: {str(e)}")
            logger.error(f"SMTP Error details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Email delivery failed: {type(e).__name__} - {str(e)}"

    return "Student email not found"


@celery.task(bind=True, name='cleanup_old_applications')
def cleanup_old_applications(self):
    """Clean up old withdrawn or rejected applications."""
    from models import db
    from models.application import Application
    
    # Get applications older than 6 months
    cutoff_date = datetime.utcnow() - timedelta(days=180)
    
    old_apps = Application.query.filter(
        Application.status.in_(['withdrawn', 'rejected']),
        Application.updated_at < cutoff_date
    ).all()
    
    count = len(old_apps)
    
    for app in old_apps:
        db.session.delete(app)
    
    db.session.commit()
    
    return f"Cleaned up {count} old applications"
