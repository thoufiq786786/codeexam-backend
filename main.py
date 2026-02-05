from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import admin_collection,questions_collection,results_collection,students_collection
from typing import List, Dict, Optional
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime,time
from passlib.context import CryptContext
import httpx
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
# FIX: Ensure CORSMiddleware is added immediately after app initialization
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["https://codeexam-frontend.vercel.app"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Explicitly include OPTIONS
    allow_headers=["*"],
)
# Define the structure of a single Test Case
class TestCaseSchema(BaseModel):
    id: Optional[str] = None
    input: str
    expectedOutput: str
    isHidden: bool

# Define the structure of the Starter Code
class StarterCodeSchema(BaseModel):
    python: str
    java: str

# Main Question Schema
class QuestionSchema(BaseModel):
    title: str
    description: str
    difficulty: str
    marks: int
    sampleInput: str
    sampleOutput: str
    testCases: List[TestCaseSchema]
    starterCode: StarterCodeSchema
    solution: str

class LoginSchema(BaseModel):
    username: str
    password: str
#Admin result
class AnswerSchema(BaseModel):
    questionId: str
    code: str
    language: str
    passed: bool
    marks: int
class TestResultSchema(BaseModel):
    studentName: str
    rollNumber: str
    obtainedMarks: int
    totalMarks: int
    correctAnswers: int
    wrongAnswers: int
    timeTaken: int
    answers: List[AnswerSchema] # Make sure this is included!
    submittedAt: datetime = None

#Student Register
class StudentRegisterSchema(BaseModel):
    name: str
    rollNumber: str
    password: str
#Answer


@app.post("/api/admin/login")
async def admin_login(data: LoginSchema):
    # Search for the admin in MongoDB
    admin = await admin_collection.find_one({
        "username": data.username,
        "password": data.password
    })

    if admin:
        return {
            "success": True, 
            "message": "Login successful", 
            "user": {"username": admin["username"], "role": "admin"}
        }
    
    raise HTTPException(status_code=401, detail="Invalid admin credentials")
# Ensure your endpoint uses the imported collection
@app.post("/api/admin/questions")
async def add_new_question(question: QuestionSchema):
    question_dict = question.dict()
    try:
        # This will now work because questions_collection is defined
        result = await questions_collection.insert_one(question_dict)
        return {
            "success": True,
            "message": "Question added successfully",
            "questionId": str(result.inserted_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
# 1. GET all questions
@app.get("/api/admin/questions")
async def get_all_questions():
    questions = []
    # Fetch all documents from the questions collection
    async for question in questions_collection.find():
        # Convert the MongoDB ObjectId to a string for the frontend
        question["id"] = str(question["_id"])
        del question["_id"] # Remove the original _id key
        questions.append(question)
    return questions
# FIX: This route allows the Edit page to find and show the question data
@app.get("/api/admin/questions/{question_id}")
async def get_single_question(question_id: str):
    try:
        # Search MongoDB for the specific ID
        question = await questions_collection.find_one({"_id": ObjectId(question_id)})
        if question:
            # Convert MongoDB's _id to a string 'id' for the frontend
            question["id"] = str(question["_id"])
            del question["_id"]
            return question
        raise HTTPException(status_code=404, detail="Question not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

# FIX: This route saves the updated data back to MongoDB
@app.put("/api/admin/questions/{question_id}")
async def update_question(question_id: str, question: QuestionSchema):
    try:
        update_data = question.dict()
        result = await questions_collection.update_one(
            {"_id": ObjectId(question_id)}, 
            {"$set": update_data}
        )
        if result.modified_count == 1:
            return {"success": True, "message": "Question updated successfully"}
        return {"success": True, "message": "No changes made"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# 2. DELETE a question by ID
@app.post("/api/admin/questions/delete/{question_id}")
async def remove_question(question_id: str):
    try:
        result = await questions_collection.delete_one({"_id": ObjectId(question_id)})
        if result.deleted_count == 1:
            return {"success": True, "message": "Question deleted successfully"}
        raise HTTPException(status_code=404, detail="Question not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
@app.post("/api/student/submit-test")
async def submit_test(result: TestResultSchema):
    new_result = await results_collection.insert_one(result.dict())
    return {"success": True, "id": str(new_result.inserted_id)}

@app.get("/api/admin/results")
async def get_all_results():
    results = []
    # Sort by obtainedMarks descending (-1)
    async for res in results_collection.find().sort("obtainedMarks", -1):
        res["id"] = str(res["_id"])
        del res["_id"]
        results.append(res)
    return results

#Student Register Route
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@app.post("/api/student/register")
async def register_student(data: StudentRegisterSchema):
    existing_student = await students_collection.find_one({"rollNumber": data.rollNumber})
    if existing_student:
        raise HTTPException(status_code=400, detail="Roll number already registered")

    # HASH THE PASSWORD HERE
    hashed_password = get_password_hash(data.password)

    student_dict = {
        "name": data.name,
        "rollNumber": data.rollNumber,
        "password": hashed_password, # Store the hash, not the plain text
        "role": "student",
        "createdAt": datetime.now()
    }

    await students_collection.insert_one(student_dict)
    return {"success": True, "message": "Registration successful"}

@app.post("/api/student/login")
async def student_login(data: LoginSchema):
    # 1. Search for the student by rollNumber (which acts as the username)
    student = await students_collection.find_one({"rollNumber": data.username})
    
    # 2. Check if student exists and verify the hashed password
    if not student or not verify_password(data.password, student["password"]):
        raise HTTPException(
            status_code=401, 
            detail="Invalid roll number or password"
        )

    # 3. Return student data (exclude the hashed password)
    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "name": student["name"],
            "rollNumber": student["rollNumber"],
            "role": "student"
        }
    }

# student submit test
@app.post("/api/student/save-result")
async def save_student_result(result: TestResultSchema):
    try:
        # 1. Prepare the update operation
        update_op = {
            # $inc adds the value to the existing field in the database
            "$inc": {
                "obtainedMarks": result.obtainedMarks, # Adds new marks to old total
                "correctAnswers": result.correctAnswers # Increments count of correct ones
            },
            # $set updates static information
            "$set": {
                "studentName": result.studentName,
                "totalMarks": result.totalMarks,
                "submittedAt": datetime.now()
            },
            # $addToSet appends the answer only if it doesn't already exist
            "$addToSet": {
                "answers": { "$each": [a.dict() for a in result.answers] }
            }
        }

        # 2. Execute the update based on rollNumber
        await results_collection.update_one(
            {"rollNumber": result.rollNumber},
            update_op,
            upsert=True # Creates the record if it's the first problem solved
        )
        
        return {"success": True, "message": "Result appended and marks incremented"}
    except Exception as e:
        print(f"Update error: {e}")
        raise HTTPException(status_code=500, detail="Database update failed")
#compilor section
PISTON_URL = "https://emkc.org/api/v2/piston/execute"
@app.post("/api/student/execute")
async def execute_code(data: dict):
    # Map frontend names to Piston's supported versions
    language_map = {
        "python": {"language": "python", "version": "3.10.0"},
        "java": {"language": "java", "version": "15.0.2"}
    }
    
    lang_info = language_map.get(data['language'])
    if not lang_info:
        raise HTTPException(status_code=400, detail="Unsupported language")
    
    payload = {
        "language": lang_info["language"],
        "version": lang_info["version"],
        "files": [{"content": data['source']}],
        "stdin": data.get('input', "")
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(PISTON_URL, json=payload, timeout=10.0)
            result = response.json()
            
            # Extract output from Piston's response
            run_data = result.get("run", {})
            return {
                "output": run_data.get("output", ""),
                "stderr": run_data.get("stderr", ""),
                "success": run_data.get("code") == 0
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compiler error: {str(e)}")
@app.get("/api/student/check-submission/{roll_number}")
async def check_submission(roll_number: str):
    # Find the student's result
    result = await results_collection.find_one({"rollNumber": roll_number})
    
    if result:
        # Extract the IDs of questions they already finished
        answered_ids = [a["questionId"] for a in result.get("answers", [])]
        return {
            "hasSubmitted": False, # Keep as false so they can enter the dashboard
            "completedIds": answered_ids
        }
    return {"hasSubmitted": False, "completedIds": []}
@app.get("/api/student/result/{roll_number}")
async def get_student_result(roll_number: str):
    # Find the student's result record
    result = await results_collection.find_one({"rollNumber": roll_number})
    
    if result:
        # MongoDB returns a document with an _id and answers list
        result["id"] = str(result["_id"])
        del result["_id"]
        return result
    
    raise HTTPException(status_code=404, detail="No test results found for this student.")