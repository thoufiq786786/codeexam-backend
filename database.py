import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Get the URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")

# Initialize the MongoDB Client
client = AsyncIOMotorClient(MONGO_URI)

# Select the database (it will be created automatically if it doesn't exist)
database = client.code_arena

# Select the collection for admins
admin_collection = database.get_collection("admins")
questions_collection = database.get_collection("questions")
results_collection = database.get_collection("results")
students_collection = database.get_collection("students")

async def test_connection():
    try:
        # The ping command is cheap and does not require auth
        await client.admin.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Connection failed: {e}")