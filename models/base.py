from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv 
import os 

# 1. Load Environment Variables
load_dotenv() 

# 2. Build the Connection String Securely
DB_USER = os.getenv("DB_USER") 
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Construct the database URL string
DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 3. Define the Base Class for all Models
Base = declarative_base()

# 4. Create the Engine
engine = create_engine(DATABASE_URL, echo=False)

# 5. Create a configured "Session" class
# This will be used in db_init.py and your service files
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all tables defined by Base.metadata in the database"""
    Base.metadata.create_all(engine)