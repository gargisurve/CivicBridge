import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "civicbridge")
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a connection to the CivicBridge MySQL database.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            return connection

    except Error as e:
        print(f"Database connection error: {e}")

    return None


# ============================================================
# USER FUNCTIONS
# ============================================================

def create_user(name, email, password_hash):
    """
    Create a new user and return the generated user ID.
    """

    connection = get_connection()

    if not connection:
        return None

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO users
            (name, email, password_hash)
            VALUES (%s, %s, %s)
        """

        cursor.execute(query, (name, email, password_hash))

        connection.commit()

        user_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return user_id

    except Error as e:
        print(f"Error creating user: {e}")
        connection.rollback()
        connection.close()
        return None


def get_user_by_email(email):
    """
    Retrieve a user using their email address.
    """

    connection = get_connection()

    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                user_id,
                name,
                email,
                password_hash,
                created_at
            FROM users
            WHERE email = %s
        """

        cursor.execute(query, (email,))

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        return user

    except Error as e:
        print(f"Error retrieving user: {e}")
        connection.close()
        return None


# ============================================================
# COMPLAINT FUNCTIONS
# ============================================================

def create_complaint(
    user_id,
    original_complaint,
    language,
    category,
    issue=None,
    location=None,
    duration=None,
    latitude=None,
    longitude=None,
    authority=None,
    department=None
):
    """
    Save a new CivicBridge complaint.

    Returns:
        complaint_id if successful
        None if unsuccessful
    """

    connection = get_connection()

    if not connection:
        return None

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO complaints (
                user_id,
                original_complaint,
                language,
                category,
                issue,
                location,
                duration,
                latitude,
                longitude,
                authority,
                department
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """

        values = (
            user_id,
            original_complaint,
            language,
            category,
            issue,
            location,
            duration,
            latitude,
            longitude,
            authority,
            department
        )

        cursor.execute(query, values)

        connection.commit()

        complaint_id = cursor.lastrowid

        # Create the first status-history record
        status_query = """
            INSERT INTO complaint_status
            (complaint_id, status, remarks)
            VALUES (%s, %s, %s)
        """

        cursor.execute(
            status_query,
            (
                complaint_id,
                "Submitted",
                "Complaint submitted through CivicBridge."
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return complaint_id

    except Error as e:
        print(f"Error creating complaint: {e}")
        connection.rollback()
        connection.close()
        return None


def get_complaint(complaint_id):
    """
    Retrieve one complaint by complaint ID.
    """

    connection = get_connection()

    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                complaint_id,
                user_id,
                original_complaint,
                language,
                category,
                issue,
                location,
                duration,
                latitude,
                longitude,
                authority,
                department,
                status,
                created_at
            FROM complaints
            WHERE complaint_id = %s
        """

        cursor.execute(query, (complaint_id,))

        complaint = cursor.fetchone()

        cursor.close()
        connection.close()

        return complaint

    except Error as e:
        print(f"Error retrieving complaint: {e}")
        connection.close()
        return None


def get_user_complaints(user_id):
    """
    Retrieve all complaints submitted by a particular user.
    """

    connection = get_connection()

    if not connection:
        return []

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                complaint_id,
                original_complaint,
                language,
                category,
                issue,
                location,
                duration,
                authority,
                department,
                status,
                created_at
            FROM complaints
            WHERE user_id = %s
            ORDER BY created_at DESC
        """

        cursor.execute(query, (user_id,))

        complaints = cursor.fetchall()

        cursor.close()
        connection.close()

        return complaints

    except Error as e:
        print(f"Error retrieving user complaints: {e}")
        connection.close()
        return []


# ============================================================
# STATUS FUNCTIONS
# ============================================================

def update_complaint_status(complaint_id, new_status, remarks=None):
    """
    Update the current complaint status and record it
    in the complaint status history.
    """

    valid_statuses = [
        "Submitted",
        "Routed",
        "In Progress",
        "Resolved",
        "Closed"
    ]

    if new_status not in valid_statuses:
        print(f"Invalid status: {new_status}")
        return False

    connection = get_connection()

    if not connection:
        return False

    try:
        cursor = connection.cursor()

        # Update current status
        update_query = """
            UPDATE complaints
            SET status = %s
            WHERE complaint_id = %s
        """

        cursor.execute(
            update_query,
            (new_status, complaint_id)
        )

        # Add status-history record
        history_query = """
            INSERT INTO complaint_status
            (complaint_id, status, remarks)
            VALUES (%s, %s, %s)
        """

        cursor.execute(
            history_query,
            (complaint_id, new_status, remarks)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Error as e:
        print(f"Error updating complaint status: {e}")
        connection.rollback()
        connection.close()
        return False


def get_complaint_status_history(complaint_id):
    """
    Retrieve the complete status history of a complaint.
    """

    connection = get_connection()

    if not connection:
        return []

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                status_id,
                complaint_id,
                status,
                remarks,
                updated_at
            FROM complaint_status
            WHERE complaint_id = %s
            ORDER BY updated_at ASC
        """

        cursor.execute(query, (complaint_id,))

        history = cursor.fetchall()

        cursor.close()
        connection.close()

        return history

    except Error as e:
        print(f"Error retrieving status history: {e}")
        connection.close()
        return []


# ============================================================
# EVIDENCE FUNCTIONS
# ============================================================

def add_evidence(complaint_id, file_name, file_type, file_path):
    """
    Save evidence information for a complaint.
    """

    connection = get_connection()

    if not connection:
        return None

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO evidence
            (complaint_id, file_name, file_type, file_path)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (complaint_id, file_name, file_type, file_path)
        )

        connection.commit()

        evidence_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return evidence_id

    except Error as e:
        print(f"Error adding evidence: {e}")
        connection.rollback()
        connection.close()
        return None


def get_complaint_evidence(complaint_id):
    """
    Retrieve all evidence associated with a complaint.
    """

    connection = get_connection()

    if not connection:
        return []

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                evidence_id,
                complaint_id,
                file_name,
                file_type,
                file_path,
                uploaded_at
            FROM evidence
            WHERE complaint_id = %s
            ORDER BY uploaded_at ASC
        """

        cursor.execute(query, (complaint_id,))

        evidence = cursor.fetchall()

        cursor.close()
        connection.close()

        return evidence

    except Error as e:
        print(f"Error retrieving evidence: {e}")
        connection.close()
        return []


# ============================================================
# TEST / ADMIN UTILITY
# ============================================================

def delete_user(user_id):
    """
    Delete a user.

    Because of ON DELETE CASCADE in the database,
    their complaints, evidence and status history will
    also be deleted.

    This function is mainly useful for testing/admin use.
    """

    connection = get_connection()

    if not connection:
        return False

    try:
        cursor = connection.cursor()

        query = """
            DELETE FROM users
            WHERE user_id = %s
        """

        cursor.execute(query, (user_id,))

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Error as e:
        print(f"Error deleting user: {e}")
        connection.rollback()
        connection.close()
        return False

def get_or_create_user(name, email):
    """
    Retrieve an existing user by email.
    If the user does not exist, create a new user.
    
    Temporary function until full authentication is added.
    """

    existing_user = get_user_by_email(email)

    if existing_user:
        return existing_user["user_id"]

    # Temporary internal value.
    # Proper password authentication will be added later.
    temporary_password = "CIVICBRIDGE_USER_PENDING_AUTH"

    return create_user(
        name=name,
        email=email,
        password_hash=temporary_password
    )