import psycopg2
import os

# Get DB credentials from environment variables
DB_URL = os.getenv("SUPABASE_DB_URL", "postgresql://postgres:Skylanders%4099@db.byzlrpfpbezlwhwumxrc.supabase.co:5432/postgres")

def get_connection():
    return psycopg2.connect(DB_URL)
