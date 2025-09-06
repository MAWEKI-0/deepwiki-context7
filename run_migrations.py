import psycopg2
import traceback
from src.config import Settings

def run_migrations():
    """
    Connects to the Supabase database and applies the SQL migrations.
    """
    try:
        print("Loading settings...")
        settings = Settings()
        print("Settings loaded.")
        print("Connecting to the database...")
        conn = psycopg2.connect(settings.SUPABASE_CONNECTION_STRING)
        cursor = conn.cursor()
        print("Connection successful.")

        # Read and execute the first migration
        with open("supabase/migrations/20250824000000_create_ads_table.sql", "r") as f:
            create_ads_table_sql = f.read()
            print("Executing create_ads_table.sql...")
            cursor.execute(create_ads_table_sql)
            print("...done.")

        # Read and execute the second migration
        with open("supabase/migrations/20250825000000_create_match_documents_adaptive_function.sql", "r") as f:
            create_function_sql = f.read()
            print("Executing create_match_documents_adaptive_function.sql...")
            cursor.execute(create_function_sql)
            print("...done.")

        conn.commit()
        cursor.close()
        conn.close()
        print("Migrations applied successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    run_migrations()
