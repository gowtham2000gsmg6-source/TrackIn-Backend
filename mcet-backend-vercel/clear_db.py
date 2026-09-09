from database import SessionLocal
import models

def clear_db():
    db = SessionLocal()
    try:
        # Delete location history entries
        db.query(models.Location).delete()
        # Delete visitor entries
        db.query(models.Visitor).delete()
        db.commit()
        print("Successfully cleared all visitor registrations and GPS history.")
    except Exception as e:
        db.rollback()
        print(f"Error clearing database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_db()
