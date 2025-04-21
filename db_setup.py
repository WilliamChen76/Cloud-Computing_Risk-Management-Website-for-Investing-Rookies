import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database credentials from environment variables
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_ENDPOINT = os.environ.get("DB_ENDPOINT")
DB_PORT = os.environ.get("DB_PORT", "5432")

if not all([DB_PASSWORD, DB_ENDPOINT]):
    print("Error: Database credentials are missing. Please check your .env file.")
    sys.exit(1)

def setup_databases():
    # Connect to the default PostgreSQL database
    conn = psycopg2.connect(
        host=DB_ENDPOINT,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database="postgres"  # Default database in PostgreSQL
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Create login_db if it doesn't exist
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'login_db'")
    if not cursor.fetchone():
        print("Creating login_db...")
        cursor.execute("CREATE DATABASE login_db")
        print("login_db created successfully")
    else:
        print("login_db already exists")
    
    # Create profile_db if it doesn't exist
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'profile_db'")
    if not cursor.fetchone():
        print("Creating profile_db...")
        cursor.execute("CREATE DATABASE profile_db")
        print("profile_db created successfully")
    else:
        print("profile_db already exists")
    
    cursor.close()
    conn.close()
    
    print("Database setup complete")

if __name__ == "__main__":
    setup_databases()