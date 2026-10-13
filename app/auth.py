import hashlib
import hmac
import re
import secrets

from database import get_connection, get_user_by_email


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

HASH_ITERATIONS = 260000


def _hash_password(password):
    salt = secrets.token_bytes(16)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS
    )

    return (
        f"pbkdf2_sha256${HASH_ITERATIONS}$"
        f"{salt.hex()}${derived.hex()}"
    )


def _verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, hash_hex = (
            stored_hash.split("$")
        )

        if algorithm != "pbkdf2_sha256":
            return False

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations)
        )

        return hmac.compare_digest(
            derived.hex(),
            hash_hex
        )

    except Exception:
        return False


def validate_email(email):
    return bool(
        EMAIL_PATTERN.match(
            email.strip()
        )
    )


def register_user(name, email, password):
    name = name.strip()
    email = email.strip().lower()

    if not name:
        return False, "Please enter your name."

    if len(name) > 100:
        return False, "Name must be 100 characters or fewer."

    if not validate_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if get_user_by_email(email):
        return False, (
            "An account with this email already exists. "
            "Please sign in."
        )

    password_hash = _hash_password(password)

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                password_hash
            )
        )

        connection.commit()

        return True, {
            "user_id": cursor.lastrowid,
            "name": name,
            "email": email
        }

    except Exception:
        if connection:
            connection.rollback()

        return False, (
            "The account could not be created. "
            "Please try again."
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def authenticate_user(email, password):
    email = email.strip().lower()

    user = get_user_by_email(email)

    if not user:
        return False, "No account was found with this email."

    stored_hash = str(
        user.get(
            "password_hash",
            ""
        )
    )

    if stored_hash == "CIVICBRIDGE_USER_PENDING_AUTH":
        return False, (
            "This account was created before secure login was "
            "enabled. Please create a new account."
        )

    if not _verify_password(
        password,
        stored_hash
    ):
        return False, "Incorrect email or password."

    return True, {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"]
    }
