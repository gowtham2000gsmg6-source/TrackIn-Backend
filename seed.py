from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
import models
import auth
from datetime import datetime, timedelta
import random

def seed_db():
    # Make sure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Admin
        admin_username = "admin"
        existing_admin = db.query(models.Admin).filter(models.Admin.username == admin_username).first()
        if not existing_admin:
            hashed_pwd = auth.hash_password("admin123")
            admin = models.Admin(username=admin_username, hashed_password=hashed_pwd)
            db.add(admin)
            print("Seeded Admin: admin / admin123")
        else:
            print("Admin already exists")

        # 2. Seed Mock Visitors (only if the visitor table is empty)
        if db.query(models.Visitor).count() == 0:
            # MCET campus center approx coordinates: Lat: 10.5983, Lng: 77.0270
            mcet_lat, mcet_lng = 10.5983, 77.0270

            # List of departments and purposes
            depts = ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical", "Civil"]
            people = ["Dr. Ramasamy (HOD)", "Dr. Chitra (Prof)", "Mr. Arunkumar (Registrar)", "Dr. Suresh (Principal)"]
            purposes = ["Project Review", "Guest Lecture", "Official Meeting", "Admission Enquiry"]

            # Visitor 1: Active inside campus
            v1_id = "MCET-0001"
            v1 = models.Visitor(
                visitor_id=v1_id,
                full_name="Rajesh Kumar",
                phone_number="9876543210",
                email="rajesh@gmail.com",
                department="Information Technology",
                person_to_meet="Dr. Ramasamy (HOD)",
                purpose="Guest Lecture",
                entry_time=datetime.utcnow() - timedelta(minutes=45),
                status="Inside",
                device_info="iPhone 14 Pro",
                browser_info="Mobile Safari"
            )
            db.add(v1)

            # Visitor 2: Active inside campus (different department)
            v2_id = "MCET-0002"
            v2 = models.Visitor(
                visitor_id=v2_id,
                full_name="Priya Sharma",
                phone_number="8765432109",
                email="priya@yahoo.com",
                department="Computer Science",
                person_to_meet="Dr. Chitra (Prof)",
                purpose="Project Review",
                entry_time=datetime.utcnow() - timedelta(minutes=30),
                status="Inside",
                device_info="OnePlus 11",
                browser_info="Chrome Mobile"
            )
            db.add(v2)

            # Visitor 3: Exited visitor
            v3_id = "MCET-0003"
            v3 = models.Visitor(
                visitor_id=v3_id,
                full_name="Amit Patel",
                phone_number="7654321098",
                email="amit@outlook.com",
                department="Mechanical",
                person_to_meet="Mr. Arunkumar (Registrar)",
                purpose="Admission Enquiry",
                entry_time=datetime.utcnow() - timedelta(hours=2),
                exit_time=datetime.utcnow() - timedelta(minutes=15),
                status="Exited",
                device_info="Samsung Galaxy S23",
                browser_info="Samsung Internet"
            )
            db.add(v3)

            db.commit()

            # Seed location paths
            # V1 Path: starting at gate, moving north-east into IT block
            v1_path = [
                (10.5975, 77.0260, 15.0), # gate
                (10.5978, 77.0263, 12.0),
                (10.5981, 77.0267, 8.0),
                (10.5984, 77.0270, 5.0), # IT block
            ]
            for i, (lat, lng, acc) in enumerate(v1_path):
                loc = models.Location(
                    visitor_id=v1_id,
                    latitude=lat,
                    longitude=lng,
                    accuracy=acc,
                    speed=1.5 if i < 3 else 0.0,
                    heading=45.0,
                    timestamp=datetime.utcnow() - timedelta(minutes=45 - i * 10),
                    source="GPS"
                )
                db.add(loc)

            # V2 Path: starting at gate, moving north-west into CSE block
            v2_path = [
                (10.5975, 77.0260, 18.0), # gate
                (10.5979, 77.0258, 10.0),
                (10.5983, 77.0256, 5.0), # CSE block
            ]
            for i, (lat, lng, acc) in enumerate(v2_path):
                loc = models.Location(
                    visitor_id=v2_id,
                    latitude=lat,
                    longitude=lng,
                    accuracy=acc,
                    speed=1.2 if i < 2 else 0.0,
                    heading=315.0,
                    timestamp=datetime.utcnow() - timedelta(minutes=30 - i * 10),
                    source="GPS"
                )
                db.add(loc)

            # V3 Path (exited): gate -> Mechanical block -> gate -> exit
            v3_path = [
                (10.5975, 77.0260, 14.0),
                (10.5978, 77.0275, 10.0), # Mech block
                (10.5976, 77.0274, 8.0),
                (10.5975, 77.0260, 15.0), # checkout at gate
            ]
            for i, (lat, lng, acc) in enumerate(v3_path):
                loc = models.Location(
                    visitor_id=v3_id,
                    latitude=lat,
                    longitude=lng,
                    accuracy=acc,
                    speed=1.8,
                    heading=180.0,
                    timestamp=datetime.utcnow() - timedelta(hours=2 - i * 15),
                    source="GPS"
                )
                db.add(loc)

            db.commit()
            print("Seeded mock visitor trails and history around MCET campus.")
        else:
            print("Visitor trails already seeded.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
