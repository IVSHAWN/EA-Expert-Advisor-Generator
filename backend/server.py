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

class MT5AccountResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    account_number: str
    server: str
    connected: bool
    created_at: str

class BotStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ea_id: str
    is_active: bool

class BotStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ea_id: str
    is_active: bool
    last_updated: str

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
Generate a MetaTrader 5 {data.type.upper()} with the following requirements:

Description: {data.description}
{f'Strategy Details: {data.strategy_details}' if data.strategy_details else ''}

Provide complete, production-ready MQL5 code with:
- Proper error handling
- Input parameters
- Trading logic
- Risk management
- Comments explaining the code

Respond ONLY with the MQL5 code, no explanations.
"""
        
        # Use GPT-4o to generate code (stable and fast)
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"ea_gen_{user['id']}_{datetime.now(timezone.utc).timestamp()}",
            system_message="You are an expert MQL5 developer creating MetaTrader 5 Expert Advisors and Indicators."
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=prompt)
        code = await chat.send_message(user_message)
        
        # Generate license key
        license_key = f"EA-{secrets.token_hex(16).upper()}"
        
        # Extract name from description
        name = data.description[:50] if len(data.description) > 50 else data.description
        
        ea_id = str(uuid.uuid4())
        ea_doc = {
            "id": ea_id,
            "user_id": user["id"],
            "type": data.type,
            "name": name,
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
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.mt5_accounts.insert_one(account_doc)
    
    return MT5AccountResponse(
        id=account_id,
        user_id=user["id"],
        account_number=data.account_number,
        server=data.server,
        connected=True,
        created_at=account_doc["created_at"]
    )

@api_router.get("/mt5/accounts", response_model=List[MT5AccountResponse])
async def get_mt5_accounts(user: dict = Depends(get_current_user)):
    accounts = await db.mt5_accounts.find({"user_id": user["id"]}, {"_id": 0, "password": 0}).to_list(1000)
    return accounts

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