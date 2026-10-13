import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from database import get_connection


STATUSES = [
    "Submitted",
    "Routed",
    "In Progress",
    "Resolved",
    "Closed",
]


def _fetch_all(sql, params=()):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def _fetch_one(sql, params=()):
    rows = _fetch_all(sql, params)
    return rows[0] if rows else None


def get_admin_stats():
    sql = """
        SELECT
            COUNT(*) AS total,
            SUM(status = 'Submitted') AS submitted,
            SUM(status = 'Routed') AS routed,
            SUM(status = 'In Progress') AS in_progress,
            SUM(status = 'Resolved') AS resolved,
            SUM(status = 'Closed') AS closed
        FROM complaints
    """

    row = _fetch_one(sql) or {}

    return {
        key: int(row.get(key) or 0)
        for key in [
            "total",
            "submitted",
            "routed",
            "in_progress",
            "resolved",
            "closed",
        ]
    }


def get_admin_complaints(
    status=None,
    department=None,
    search=None,
):
    sql = """
        SELECT
            c.complaint_id,
            c.user_id,
            u.name AS citizen_name,
            u.email AS citizen_email,
            c.original_complaint,
            c.language,
            c.category,
            c.issue,
            c.location,
            c.duration,
            c.latitude,
            c.longitude,
            c.authority,
            c.department,
            c.status,
            c.created_at
        FROM complaints c
        INNER JOIN users u
            ON c.user_id = u.user_id
        WHERE 1 = 1
    """

    params = []

    if status and status != "All":
        sql += " AND c.status = %s"
        params.append(status)

    if department and department != "All":
        sql += " AND c.department = %s"
        params.append(department)

    if search:
        sql += """
            AND (
                CAST(c.complaint_id AS CHAR) LIKE %s
                OR c.original_complaint LIKE %s
                OR c.location LIKE %s
                OR u.name LIKE %s
                OR u.email LIKE %s
            )
        """
        term = f"%{search}%"
        params.extend([term] * 5)

    sql += " ORDER BY c.created_at DESC"

    return _fetch_all(sql, tuple(params))


def get_admin_complaint(complaint_id):
    return _fetch_one(
        """
        SELECT
            c.*,
            u.name AS citizen_name,
            u.email AS citizen_email
        FROM complaints c
        INNER JOIN users u
            ON c.user_id = u.user_id
        WHERE c.complaint_id = %s
        """,
        (complaint_id,),
    )


def get_admin_status_history(complaint_id):
    return _fetch_all(
        """
        SELECT
            status_id,
            complaint_id,
            status,
            remarks,
            updated_at
        FROM complaint_status
        WHERE complaint_id = %s
        ORDER BY updated_at ASC, status_id ASC
        """,
        (complaint_id,),
    )


def get_admin_evidence(complaint_id):
    return _fetch_all(
        """
        SELECT
            evidence_id,
            complaint_id,
            file_name,
            file_type,
            file_path,
            uploaded_at
        FROM evidence
        WHERE complaint_id = %s
        ORDER BY uploaded_at ASC, evidence_id ASC
        """,
        (complaint_id,),
    )


def get_department_list():
    rows = _fetch_all(
        """
        SELECT DISTINCT
            department,
            authority
        FROM complaints
        WHERE department IS NOT NULL
          AND department <> ''
        ORDER BY department
        """
    )

    return rows


def forward_complaint(
    complaint_id,
    department,
    authority,
    remarks,
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE complaints
            SET authority = %s,
                department = %s,
                status = 'Routed'
            WHERE complaint_id = %s
            """,
            (
                authority,
                department,
                complaint_id,
            ),
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return False

        final_remarks = (
            remarks.strip()
            if remarks and remarks.strip()
            else f"Forwarded to {department}."
        )

        cursor.execute(
            """
            INSERT INTO complaint_status
            (complaint_id, status, remarks)
            VALUES (%s, 'Routed', %s)
            """,
            (
                complaint_id,
                final_remarks,
            ),
        )

        connection.commit()
        return True

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def update_admin_status(
    complaint_id,
    status,
    remarks,
):
    if status not in STATUSES:
        raise ValueError("Invalid complaint status.")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE complaints
            SET status = %s
            WHERE complaint_id = %s
            """,
            (
                status,
                complaint_id,
            ),
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return False

        final_remarks = (
            remarks.strip()
            if remarks and remarks.strip()
            else f"Status updated to {status}."
        )

        cursor.execute(
            """
            INSERT INTO complaint_status
            (complaint_id, status, remarks)
            VALUES (%s, %s, %s)
            """,
            (
                complaint_id,
                status,
                final_remarks,
            ),
        )

        connection.commit()
        return True

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
