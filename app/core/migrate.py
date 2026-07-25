"""Auto-migration script - Adds missing columns/tables"""
from sqlalchemy import inspect, text
from app.core.database import engine, Base
from app.models.user import User  # Import all models

def migrate_database():
    """Add missing columns/tables to existing database"""
    
    inspector = inspect(engine)
    
    # Get existing tables
    existing_tables = inspector.get_table_names()
    
    print(f"\n🔍 Checking database schema...")
    print(f"📊 Existing tables: {existing_tables}\n")
    
    # Create new tables (won't recreate existing ones)
    Base.metadata.create_all(bind=engine)
    print("✅ Tables synced\n")
    
    # Check users table columns
    if 'users' in existing_tables:
        existing_columns = {col['name'] for col in inspector.get_columns('users')}
        
        required_columns = {
            'verification_token': 'VARCHAR(255)',
            'verification_token_expires': 'TIMESTAMP WITH TIME ZONE',
            'verification_sent_at': 'TIMESTAMP WITH TIME ZONE',
        }
        
        missing_columns = []
        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                missing_columns.append((col_name, col_type))
        
        if missing_columns:
            print(f"⚠️  Missing columns in 'users' table:")
            for col_name, col_type in missing_columns:
                print(f"   - {col_name} ({col_type})")
            
            # Add missing columns
            with engine.begin() as conn:
                for col_name, col_type in missing_columns:
                    sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                    try:
                        conn.execute(text(sql))
                        print(f"   ✅ Added: {col_name}")
                    except Exception as e:
                        print(f"   ❌ Failed to add {col_name}: {e}")
            
            print("\n✅ Migration complete!\n")
        else:
            print("✅ All columns exist\n")

if __name__ == "__main__":
    migrate_database()