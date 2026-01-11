import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def show_enums():
    print("🔍 Fetching 'facture_statut' ENUM values...")
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT unnest(enum_range(NULL::facture_statut))")
            rows = cur.fetchall()
            labels = [r[0] for r in rows]
            print(f"Values: {labels}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    show_enums()
