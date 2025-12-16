import os
import getpass
import psycopg2
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ["DATABASE_URL"]

def main():
    email = input("Email: ").strip().lower()
    first_name = input("First name (optional): ").strip() or None
    last_name = input("Last name (optional): ").strip() or None
    password = getpass.getpass("Password: ")

    pw_hash = generate_password_hash(password, method="pbkdf2:sha256")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (email, password_hash, first_name, last_name, role)
        VALUES (%s, %s, %s, %s, 'owner')
        ON CONFLICT (email) DO NOTHING
        RETURNING id
        """,
        (email, pw_hash, first_name, last_name),
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if row:
        print(f"Created user id={row[0]}")
    else:
        print("User already exists (no changes).")

if __name__ == "__main__":
    main()
