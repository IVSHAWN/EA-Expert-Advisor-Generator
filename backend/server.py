from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me-in-production')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class GenerateEARequest(BaseModel):
    type: str  # "ea" or "indicator"
    name: str
    description: str
    strategy_details: Optional[str] = None

class ExpertAdvisor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    type: str
    name: str
    description: str
    code: str
    license_key: str
    created_at: str

class MT5Account(BaseModel):
    account_number: str
    server: str
    password: str
    balance: Optional[float] = None
    equity: Optional[float] = None
    margin: Optional[float] = None
    free_margin: Optional[float] = None

class MT5AccountResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    account_number: str
    server: str
    connected: bool
    balance: Optional[float] = None
    equity: Optional[float] = None
    margin: Optional[float] = None
    free_margin: Optional[float] = None
    created_at: str

class MT5BalanceUpdate(BaseModel):
    balance: float
    equity: Optional[float] = None
    margin: Optional[float] = None
    free_margin: Optional[float] = None

class BotStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ea_id: str
    is_active: bool

class BotStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ea_id: str
    is_active: bool
    last_updated: str

class LicenseAssignment(BaseModel):
    license_key: str
    customer_name: str
    customer_email: EmailStr
    expiration_date: Optional[str] = None
    purchase_amount: Optional[float] = None

class LicenseAssignmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    ea_id: str
    license_key: str
    customer_name: str
    customer_email: str
    assigned_date: str
    expiration_date: Optional[str] = None
    purchase_amount: Optional[float] = None
    is_active: bool
    last_used: Optional[str] = None
    usage_count: int

class LicenseValidation(BaseModel):
    license_key: str
    mt5_account: Optional[str] = None

class LicenseAnalytics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ea_id: str
    ea_name: str
    total_licenses: int
    active_licenses: int
    expired_licenses: int
    total_revenue: float
    licenses: List[LicenseAssignmentResponse]

# Auth helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Routes
@api_router.get("/")
async def root():
    return {"message": "EA Generator API"}

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserRegister):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"user_id": user_id})
    user = User(id=user_id, email=data.email, name=data.name, created_at=user_doc["created_at"])
    return TokenResponse(access_token=token, user=user)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"user_id": user["id"]})
    user_response = User(id=user["id"], email=user["email"], name=user["name"], created_at=user["created_at"])
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/ea/generate", response_model=ExpertAdvisor)
async def generate_ea(data: GenerateEARequest, user: dict = Depends(get_current_user)):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Create prompt for EA generation
        prompt = f"""
You are an expert MQL5 developer for MetaTrader 5. Generate a complete, error-free {data.type.upper()} that will compile successfully in MetaEditor Build 3770+.

Requirements:
Description: {data.description}
{f'Strategy Details: {data.strategy_details}' if data.strategy_details else ''}

CRITICAL MQL5 SYNTAX RULES:
1. DO NOT use #property strict (that's MT4 only)
2. Use #property copyright, #property link, #property version
3. Include <Trade\\Trade.mqh> for CTrade class
4. Use OnInit(), OnDeinit(), OnTick() for Expert Advisors
5. Use SymbolInfoDouble() for prices, not MarketInfo()
6. Use _Symbol for current symbol, not Symbol()
7. Use _Digits for digits, not Digits
8. Use _Point for point size, not Point
9. Properly declare CTrade object globally: CTrade trade;
10. Use NormalizeDouble() for price normalization
11. Handle errors with GetLastError() and proper error codes
12. All input parameters must use 'input' keyword
13. Use proper MQL5 data types: double, int, long, string, datetime, bool
14. Comment all major logic blocks

REQUIRED STRUCTURE:
//+------------------------------------------------------------------+
//|                                                    EA_Name.mq5   |
//|                        Copyright 2025, Your Name                 |
//+------------------------------------------------------------------+
#property copyright "2025"
#property version   "1.00"

#include <Trade\\Trade.mqh>

input double LotSize = 0.1;
input int StopLoss = 50;
input int TakeProfit = 100;

CTrade trade;

int OnInit()
{{
   return(INIT_SUCCEEDED);
}}

void OnDeinit(const int reason)
{{
}}

void OnTick()
{{
   // Your trading logic here
}}

Return ONLY compilable MQL5 code without markdown, explanations, or ```code blocks```. Start directly with //.
"""
        
        # Use GPT-4o to generate code (stable and fast)
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"ea_gen_{user['id']}_{datetime.now(timezone.utc).timestamp()}",
            system_message="You are an expert MQL5 developer. Generate only valid, compilable MQL5 code without markdown formatting."
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=prompt)
        raw_code = await chat.send_message(user_message)
        
        # Clean the code - remove markdown formatting if present
        code = raw_code.strip()
        if code.startswith("```mql5") or code.startswith("```"):
            # Remove markdown code blocks
            lines = code.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]  # Remove opening ```
            if lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove closing ```
            code = '\n'.join(lines)
        
        code = code.strip()
        
        # Generate license key
        license_key = f"EA-{secrets.token_hex(16).upper()}"
        
        ea_id = str(uuid.uuid4())
        ea_doc = {
            "id": ea_id,
            "user_id": user["id"],
            "type": data.type,
            "name": data.name,
            "description": data.description,
            "code": code,
            "license_key": license_key,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.expert_advisors.insert_one(ea_doc)
        
        # Initialize bot status as inactive
        await db.bot_status.insert_one({
            "ea_id": ea_id,
            "is_active": False,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
        
        return ExpertAdvisor(
            id=ea_id,
            user_id=user["id"],
            type=data.type,
            name=name,
            description=data.description,
            code=code,
            license_key=license_key,
            created_at=ea_doc["created_at"]
        )
    except Exception as e:
        logging.error(f"EA generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate EA: {str(e)}")

@api_router.get("/ea/list", response_model=List[ExpertAdvisor])
async def list_eas(user: dict = Depends(get_current_user)):
    eas = await db.expert_advisors.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    return eas

@api_router.get("/ea/{ea_id}", response_model=ExpertAdvisor)
async def get_ea(ea_id: str, user: dict = Depends(get_current_user)):
    ea = await db.expert_advisors.find_one({"id": ea_id, "user_id": user["id"]}, {"_id": 0})
    if not ea:
        raise HTTPException(status_code=404, detail="EA not found")
    return ea

@api_router.delete("/ea/{ea_id}")
async def delete_ea(ea_id: str, user: dict = Depends(get_current_user)):
    # Verify EA belongs to user
    ea = await db.expert_advisors.find_one({"id": ea_id, "user_id": user["id"]})
    if not ea:
        raise HTTPException(status_code=404, detail="EA not found")
    
    # Delete the EA
    await db.expert_advisors.delete_one({"id": ea_id, "user_id": user["id"]})
    
    # Delete associated bot status
    await db.bot_status.delete_one({"ea_id": ea_id})
    
    # Delete associated license assignments
    await db.license_assignments.delete_many({"ea_id": ea_id})
    
    return {"message": "EA deleted successfully", "ea_id": ea_id}

@api_router.post("/mt5/connect", response_model=MT5AccountResponse)
async def connect_mt5(data: MT5Account, user: dict = Depends(get_current_user)):
    # Check if account already exists
    existing = await db.mt5_accounts.find_one({"user_id": user["id"], "account_number": data.account_number})
    if existing:
        raise HTTPException(status_code=400, detail="MT5 account already connected")
    
    account_id = str(uuid.uuid4())
    account_doc = {
        "id": account_id,
        "user_id": user["id"],
        "account_number": data.account_number,
        "server": data.server,
        "password": data.password,  # In production, encrypt this
        "connected": True,
        "balance": data.balance,
        "equity": data.equity,
        "margin": data.margin,
        "free_margin": data.free_margin,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.mt5_accounts.insert_one(account_doc)
    
    return MT5AccountResponse(
        id=account_id,
        user_id=user["id"],
        account_number=data.account_number,
        server=data.server,
        connected=True,
        balance=data.balance,
        equity=data.equity,
        margin=data.margin,
        free_margin=data.free_margin,
        created_at=account_doc["created_at"]
    )

@api_router.get("/mt5/accounts", response_model=List[MT5AccountResponse])
async def get_mt5_accounts(user: dict = Depends(get_current_user)):
    accounts = await db.mt5_accounts.find({"user_id": user["id"]}, {"_id": 0, "password": 0}).to_list(1000)
    return accounts

@api_router.put("/mt5/balance/{account_id}", response_model=MT5AccountResponse)
async def update_mt5_balance(account_id: str, data: MT5BalanceUpdate, user: dict = Depends(get_current_user)):
    # Verify account belongs to user
    account = await db.mt5_accounts.find_one({"id": account_id, "user_id": user["id"]})
    if not account:
        raise HTTPException(status_code=404, detail="MT5 account not found")
    
    # Update balance
    await db.mt5_accounts.update_one(
        {"id": account_id},
        {"$set": {
            "balance": data.balance,
            "equity": data.equity,
            "margin": data.margin,
            "free_margin": data.free_margin
        }}
    )
    
    updated_account = await db.mt5_accounts.find_one({"id": account_id}, {"_id": 0, "password": 0})
    return MT5AccountResponse(**updated_account)

@api_router.post("/bot/toggle", response_model=BotStatusResponse)
async def toggle_bot(data: BotStatus, user: dict = Depends(get_current_user)):
    # Verify EA belongs to user
    ea = await db.expert_advisors.find_one({"id": data.ea_id, "user_id": user["id"]})
    if not ea:
        raise HTTPException(status_code=404, detail="EA not found")
    
    # Update bot status
    await db.bot_status.update_one(
        {"ea_id": data.ea_id},
        {"$set": {
            "is_active": data.is_active,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    status_doc = await db.bot_status.find_one({"ea_id": data.ea_id}, {"_id": 0})
    return BotStatusResponse(
        ea_id=status_doc["ea_id"],
        is_active=status_doc["is_active"],
        last_updated=status_doc["last_updated"]
    )

@api_router.get("/bot/status/{ea_id}", response_model=BotStatusResponse)
async def get_bot_status(ea_id: str, user: dict = Depends(get_current_user)):
    # Verify EA belongs to user
    ea = await db.expert_advisors.find_one({"id": ea_id, "user_id": user["id"]})
    if not ea:
        raise HTTPException(status_code=404, detail="EA not found")
    
    status_doc = await db.bot_status.find_one({"ea_id": ea_id}, {"_id": 0})
    if not status_doc:
        # Initialize if not exists
        status_doc = {
            "ea_id": ea_id,
            "is_active": False,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        await db.bot_status.insert_one(status_doc)
    
    return BotStatusResponse(
        ea_id=status_doc["ea_id"],
        is_active=status_doc["is_active"],
        last_updated=status_doc["last_updated"]
    )

# License Management Endpoints
@api_router.post("/license/assign", response_model=LicenseAssignmentResponse)
async def assign_license(ea_id: str, data: LicenseAssignment, user: dict = Depends(get_current_user)):
    # Verify EA belongs to user
    ea = await db.expert_advisors.find_one({"id": ea_id, "user_id": user["id"]})
    if not ea:
        raise HTTPException(status_code=404, detail="EA not found")
    
    # Check if license key belongs to this EA
    if ea["license_key"] != data.license_key:
        raise HTTPException(status_code=400, detail="License key does not match this EA")
    
    # Check if license already assigned
    existing = await db.license_assignments.find_one({"license_key": data.license_key})
    if existing:
        raise HTTPException(status_code=400, detail="License key already assigned")
    
    assignment_id = str(uuid.uuid4())
    assignment_doc = {
        "id": assignment_id,
        "ea_id": ea_id,
        "license_key": data.license_key,
        "customer_name": data.customer_name,
        "customer_email": data.customer_email,
        "assigned_date": datetime.now(timezone.utc).isoformat(),
        "expiration_date": data.expiration_date,
        "purchase_amount": data.purchase_amount or 0.0,
        "is_active": True,
        "last_used": None,
        "usage_count": 0
    }
    await db.license_assignments.insert_one(assignment_doc)
    
    return LicenseAssignmentResponse(**assignment_doc)

@api_router.get("/license/analytics/{ea_id}", response_model=LicenseAnalytics)
async def get_license_analytics(ea_id: str, user: dict = Depends(get_current_user)):
    # Verify EA belongs to user
    ea = await db.expert_advisors.find_one({"id": ea_id, "user_id": user["id"]})
    if not ea:
        raise HTTPException(status_code=404, detail="EA not found")
    
    # Get all license assignments for this EA
    assignments = await db.license_assignments.find({"ea_id": ea_id}, {"_id": 0}).to_list(1000)
    
    total_licenses = len(assignments)
    active_licenses = 0
    expired_licenses = 0
    total_revenue = 0.0
    
    now = datetime.now(timezone.utc)
    
    for assignment in assignments:
        # Check if expired
        if assignment.get("expiration_date"):
            exp_date = datetime.fromisoformat(assignment["expiration_date"])
            if exp_date < now:
                assignment["is_active"] = False
                expired_licenses += 1
            else:
                active_licenses += 1
        else:
            active_licenses += 1
        
        total_revenue += assignment.get("purchase_amount", 0.0)
    
    return LicenseAnalytics(
        ea_id=ea_id,
        ea_name=ea["name"],
        total_licenses=total_licenses,
        active_licenses=active_licenses,
        expired_licenses=expired_licenses,
        total_revenue=total_revenue,
        licenses=[LicenseAssignmentResponse(**a) for a in assignments]
    )

@api_router.post("/license/validate")
async def validate_license(data: LicenseValidation):
    """Public endpoint for MT5 EAs to validate licenses"""
    assignment = await db.license_assignments.find_one({"license_key": data.license_key})
    
    if not assignment:
        return {"valid": False, "message": "License key not found"}
    
    # Check expiration
    if assignment.get("expiration_date"):
        exp_date = datetime.fromisoformat(assignment["expiration_date"])
        if exp_date < datetime.now(timezone.utc):
            return {"valid": False, "message": "License expired"}
    
    # Update usage stats
    await db.license_assignments.update_one(
        {"license_key": data.license_key},
        {
            "$set": {"last_used": datetime.now(timezone.utc).isoformat()},
            "$inc": {"usage_count": 1}
        }
    )
    
    # Log usage
    await db.license_usage_log.insert_one({
        "license_key": data.license_key,
        "mt5_account": data.mt5_account,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "valid": True,
        "customer_name": assignment["customer_name"],
        "expiration_date": assignment.get("expiration_date")
    }

@api_router.get("/license/usage/{license_key}")
async def get_license_usage(license_key: str, user: dict = Depends(get_current_user)):
    """Get usage history for a license key"""
    # Verify license belongs to user's EA
    assignment = await db.license_assignments.find_one({"license_key": license_key})
    if not assignment:
        raise HTTPException(status_code=404, detail="License not found")
    
    ea = await db.expert_advisors.find_one({"id": assignment["ea_id"], "user_id": user["id"]})
    if not ea:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get usage logs
    logs = await db.license_usage_log.find({"license_key": license_key}, {"_id": 0}).sort("timestamp", -1).limit(100).to_list(100)
    
    return {
        "license_key": license_key,
        "usage_count": assignment.get("usage_count", 0),
        "last_used": assignment.get("last_used"),
        "recent_usage": logs
    }

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()