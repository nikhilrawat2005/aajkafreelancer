from flask import send_file, jsonify, current_app
from flask_login import login_required, current_user
import pandas as pd
from io import BytesIO

from app.admin import admin_bp
from app.models import User


@admin_bp.route('/export/users')
@login_required
def export_users():
    """Export all users to an Excel file. Only accessible by admins."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    users = User.query.all()
    data = []
    for u in users:
        data.append({
            'full_name': u.full_name,
            'username': u.username,
            'email': u.email,
            'college': u.college_name,
            'worker': u.is_worker,
            'skills': u.skills
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')
    output.seek(0)

    return send_file(
        output,
        download_name='users_export.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )