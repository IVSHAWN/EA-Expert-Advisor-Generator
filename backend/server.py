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

class EmailLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    to_email: str
    subject: str
    body: str
    email_type: str
    sent_at: str
    status: str
    error_message: Optional[str] = None

class SupportMessage(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

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
        "role": "user",  # user or admin
        "status": "pending",  # pending, active, suspended
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "ea_count": 0,
        "license_count": 0
    }
    await db.users.insert_one(user_doc)
    
    # Users with pending status can't login until approved
    return {"message": "Registration successful. Your account is pending approval.", "user_id": user_id}

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is approved
    if user.get("status") == "pending":
        raise HTTPException(status_code=403, detail="Your account is pending admin approval")
    
    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    token = create_access_token({"user_id": user["id"]})
    user_response = User(id=user["id"], email=user["email"], name=user["name"], created_at=user["created_at"])
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/ea/generate", response_model=ExpertAdvisor)
async def generate_ea(data: GenerateEARequest, user: dict = Depends(get_current_user)):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Create prompt for EA generation
        ea_name = data.name.replace(" ", "_")
        prompt = f"""
You are an MQL5 code generator. You MUST use the exact template below with NO modifications to structure.

EA Name: {data.name}
Strategy: {data.description}
{f'Details: {data.strategy_details}' if data.strategy_details else ''}

STRICT RULES - FOLLOW EXACTLY:

1. SYMBOL ACCESS (CRITICAL):
   - ALWAYS: _Symbol (with underscore)
   - NEVER: Symbol (causes "undeclared identifier" error)
   - Check EVERY occurrence

2. DIGITS:
   - ALWAYS: _Digits (with underscore)
   - NEVER: Digits

3. POINT:
   - ALWAYS: _Point (with underscore)
   - NEVER: Point

4. PRICE DATA (CRITICAL - COMMON ERROR):
   - NEVER use: Close[1], Open[1], High[1], Low[1] (MT4 syntax)
   - ALWAYS use arrays:
     double close[];
     ArraySetAsSeries(close, true);
     CopyClose(_Symbol, PERIOD_CURRENT, 0, 10, close);
     double lastClose = close[1];

5. GET CURRENT PRICES:
   - Ask: SymbolInfoDouble(_Symbol, SYMBOL_ASK)
   - Bid: SymbolInfoDouble(_Symbol, SYMBOL_BID)
   - NEVER: Ask, Bid variables

6. TRADING:
   - ALWAYS: trade.Buy() / trade.Sell()
   - NEVER: OrderSend()

7. POSITION CHECKS:
   - Use: PositionSelect(_Symbol)
   - NEVER: OrderSelect(), OrdersTotal()

8. VARIABLE INITIALIZATION (CRITICAL):
   - ALWAYS initialize variables before use
   - Example: double currentTP = 0.0;
   - NEVER use uninitialized variables

9. PROPERTIES:
   - NEVER: #property strict
   - ALWAYS: #property copyright, #property version

10. INCLUDES:
    - ALWAYS: #include <Trade\\Trade.mqh>

11. DECLARATIONS:
    - CTrade globally: CTrade trade;
    - Proper types: double, int, long, bool, string

12. FUNCTIONS:
    - int OnInit() - return INIT_SUCCEEDED
    - void OnDeinit(const int reason)
    - void OnTick()

EXACT TEMPLATE TO FOLLOW:

//+------------------------------------------------------------------+
//|                                                 {ea_name}.mq5    |
//|                        Copyright 2025, Expert Coder              |
//+------------------------------------------------------------------+
#property copyright "2025"
#property version   "1.00"

#include <Trade\\Trade.mqh>

//--- Input parameters
input double InpLotSize = 0.1;        // Lot size
input int    InpStopLoss = 50;        // Stop Loss (points)
input int    InpTakeProfit = 100;     // Take Profit (points)

//--- Global variables
CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{{
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
   // Cleanup code here
}}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{{
   // Get current prices using _Symbol (with underscore)
   double ask = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_ASK), _Digits);
   double bid = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_BID), _Digits);
   
   // Check if no position open using _Symbol (with underscore)
   if(!PositionSelect(_Symbol))
   {{
      // Calculate stop loss and take profit using _Point (with underscore)
      double sl = ask - InpStopLoss * _Point;
      double tp = ask + InpTakeProfit * _Point;
      
      // Normalize prices using _Digits (with underscore)
      sl = NormalizeDouble(sl, _Digits);
      tp = NormalizeDouble(tp, _Digits);
      
      // Place order using CTrade
      if(trade.Buy(InpLotSize, _Symbol, ask, sl, tp, "Your strategy"))
      {{
         Print("Buy order placed successfully");
      }}
   }}
}}

ADDITIONAL CRITICAL RULES TO PREVENT ERRORS:

13. INDICATOR HANDLES:
    - Declare globally: int handleMA;
    - Initialize in OnInit: handleMA = iMA(_Symbol, PERIOD_CURRENT, 20, 0, MODE_SMA, PRICE_CLOSE);
    - Check: if(handleMA == INVALID_HANDLE) return INIT_FAILED;
    - Use arrays:
      double maBuffer[];
      ArraySetAsSeries(maBuffer, true);
      CopyBuffer(handleMA, 0, 0, 3, maBuffer);
    - NEVER call iMA() in OnTick()

14. PRICE ARRAYS (AVOID Close[1] ERRORS):
    - Declare: double closePrice[];
    - Setup: ArraySetAsSeries(closePrice, true);
    - Copy: CopyClose(_Symbol, PERIOD_CURRENT, 0, 10, closePrice);
    - Use: double lastClose = closePrice[1];
    - NEVER: Close[1], Open[1], High[1], Low[1]

13. COMMENTS:
    - Use // for single line
    - Use /* */ for multi-line
    - Add space after //: // Comment (not //Comment)

14. SEMICOLONS:
    - ALWAYS end statements with semicolon ;
    - if, for, while blocks don't need semicolon after closing brace
    - Function declarations don't need semicolon

15. VARIABLE SCOPE:
    - Global variables: Outside functions
    - Local variables: Inside functions
    - NEVER redeclare same variable

CRITICAL EXAMPLES TO PREVENT ERRORS:

WRONG (MT4 - CAUSES ERRORS):
   if(Close[1] > Close[2])  // ERROR: Close not defined
   PositionSelect(Symbol)    // ERROR: Symbol undeclared
   double tp;                // ERROR: used before initialization
   if(tp > 100)             // WARNING: uninitialized variable

CORRECT (MT5 - COMPILES):
   double close[];
   ArraySetAsSeries(close, true);
   CopyClose(_Symbol, PERIOD_CURRENT, 0, 10, close);
   if(close[1] > close[2])  // CORRECT
   
   PositionSelect(_Symbol)   // CORRECT with underscore
   
   double tp = 0.0;         // CORRECT: initialized
   if(tp > 100)             // CORRECT

ULTRA-SIMPLE WORKING TEMPLATE (COPY THIS EXACTLY):

//+------------------------------------------------------------------+
//|                                          {ea_name}.mq5           |
//|                             Copyright 2025, EA Generator         |
//+------------------------------------------------------------------+
#property copyright "2025"
#property version   "1.00"

#include <Trade\\Trade.mqh>

//--- Input parameters
input double InpLotSize = 0.1;        // Lot size
input int    InpStopLoss = 100;       // Stop Loss in points
input int    InpTakeProfit = 200;     // Take Profit in points

//--- Global variables
CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{{
   Print("EA Initialized Successfully");
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
   Print("EA Deinitialized");
}}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{{
   // Get current Ask and Bid prices
   double ask = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_ASK), _Digits);
   double bid = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_BID), _Digits);
   
   // Check if we have an open position
   if(!PositionSelect(_Symbol))
   {{
      // No position open - apply trading logic here
      
      // Calculate stop loss and take profit levels
      double sl = NormalizeDouble(ask - InpStopLoss * _Point, _Digits);
      double tp = NormalizeDouble(ask + InpTakeProfit * _Point, _Digits);
      
      // Place a buy order (modify this based on your strategy)
      if(trade.Buy(InpLotSize, _Symbol, ask, sl, tp, "Buy Signal"))
      {{
         Print("Buy order executed at ", ask);
      }}
      else
      {{
         Print("Buy order failed. Error code: ", GetLastError());
      }}
   }}
}}

16. KEEP IT SIMPLE:
    - Start with basic structure
    - Add strategy logic step by step
    - Test each component
    - Don't overcomplicate

17. COMMON MISTAKES TO AVOID:
    - Missing semicolons
    - Wrong variable names
    - Undefined variables
    - Wrong function parameters
    - Missing includes

YOU MUST RETURN THIS EXACT TEMPLATE WITH ZERO MODIFICATIONS TO STRUCTURE.
ONLY add simple buy/sell logic in the marked section. NO complex code.

VERIFIED TEMPLATE (COMPILES WITH 0 ERRORS):

//+------------------------------------------------------------------+
//|                                          {ea_name}.mq5           |
//+------------------------------------------------------------------+
#property copyright "2025"
#property version   "1.00"

#include <Trade\\Trade.mqh>

input double LotSize = 0.1;
input int StopLossPips = 50;
input int TakeProfitPips = 100;

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
   double ask = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_ASK), _Digits);
   double bid = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_BID), _Digits);
   
   if(PositionSelect(_Symbol)) return;
   
   // Simple buy logic
   double sl = NormalizeDouble(ask - StopLossPips * _Point, _Digits);
   double tp = NormalizeDouble(ask + TakeProfitPips * _Point, _Digits);
   
   trade.Buy(LotSize, _Symbol, ask, sl, tp);
}}

CRITICAL RULES - FOLLOW EXACTLY:
1. Copy the template EXACTLY as shown
2. Do NOT change #property, #include, input parameters, or function signatures
3. Only modify the simple buy logic in OnTick() if needed
4. Do NOT use: PERIOD_CURRENT, PERIOD_M1, PERIOD_H1, or any Period enum
5. Use ONLY: _Symbol, _Digits, _Point, SYMBOL_ASK, SYMBOL_BID
6. Do NOT add arrays, loops, or complex logic
7. Keep it SIMPLE - just buy with stop loss and take profit
8. Return ONLY the code without markdown or explanations

For strategies described, implement SIMPLIFIED version with basic buy logic only.

Now return the template with minimal modifications.
"""
        
        # Use GPT-4o to generate code (stable and fast)
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"ea_gen_{user['id']}_{datetime.now(timezone.utc).timestamp()}",
            system_message="You are a code template copier. Return the exact template provided. Do not modify structure. Do not add complex logic. Keep OnTick() simple with basic buy/sell only. Use only _Symbol, _Digits, _Point. No enums except SYMBOL_ASK, SYMBOL_BID. No Period enums. Code must compile with ZERO errors."
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
        
        # Send license key email
        email_subject = f"Your EA License Key: {data.name}"
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #8B5CF6;">Your Expert Advisor is Ready!</h2>
            <p>Hi {user['name']},</p>
            <p>Your Expert Advisor <strong>{data.name}</strong> has been successfully generated.</p>
            
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #8B5CF6; margin-top: 0;">Your License Key:</h3>
                <p style="font-size: 18px; font-weight: bold; color: #1f2937; font-family: monospace;">
                    {license_key}
                </p>
            </div>
            
            <p><strong>What's Next?</strong></p>
            <ol>
                <li>Download your EA from the dashboard</li>
                <li>Install it in MetaTrader 5</li>
                <li>Use your license key to access the monitoring app</li>
            </ol>
            
            <p><strong>EA Details:</strong></p>
            <ul>
                <li>Name: {data.name}</li>
                <li>Type: {data.type.upper()}</li>
                <li>Description: {data.description}</li>
            </ul>
            
            <p>If you have any questions, please contact our support team.</p>
            
            <p>Happy Trading!<br>EA Generator Team</p>
        </body>
        </html>
        """
        
        await send_email(user["email"], email_subject, email_body, "license_key")
        
        return ExpertAdvisor(
            id=ea_id,
            user_id=user["id"],
            type=data.type,
            name=data.name,
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

# Email Service
async def send_email(to_email: str, subject: str, body: str, email_type: str):
    email_id = str(uuid.uuid4())
    sent_at = datetime.now(timezone.utc).isoformat()
    
    # Check if demo mode
    demo_mode = os.environ.get('EMAIL_DEMO_MODE', 'true').lower() == 'true'
    
    email_log = {
        "id": email_id,
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "email_type": email_type,
        "sent_at": sent_at,
        "status": "pending",
        "error_message": None
    }
    
    if demo_mode:
        # Demo mode - just log to database
        email_log["status"] = "demo_sent"
        await db.email_logs.insert_one(email_log)
        logging.info(f"[DEMO MODE] Email logged: {subject} to {to_email}")
        return True
    else:
        # Real mode - send via SendGrid
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            api_key = os.environ.get('SENDGRID_API_KEY')
            from_email = os.environ.get('EMAIL_FROM', 'noreply@eagenerator.com')
            
            if not api_key:
                email_log["status"] = "failed"
                email_log["error_message"] = "SendGrid API key not configured"
                await db.email_logs.insert_one(email_log)
                return False
            
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=body
            )
            
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                email_log["status"] = "sent"
            else:
                email_log["status"] = "failed"
                email_log["error_message"] = f"Status code: {response.status_code}"
            
            await db.email_logs.insert_one(email_log)
            return email_log["status"] == "sent"
            
        except Exception as e:
            email_log["status"] = "failed"
            email_log["error_message"] = str(e)
            await db.email_logs.insert_one(email_log)
            logging.error(f"Email send error: {str(e)}")
            return False

# Email Endpoints
@api_router.get("/emails/logs", response_model=List[EmailLog])
async def get_email_logs(user: dict = Depends(get_current_user)):
    # Get all email logs for user's email
    logs = await db.email_logs.find({"to_email": user["email"]}, {"_id": 0}).sort("sent_at", -1).limit(100).to_list(100)
    return logs

@api_router.get("/emails/all", response_model=List[EmailLog])
async def get_all_emails(user: dict = Depends(get_current_user)):
    # Get all emails sent from the system (for admin/dashboard view)
    logs = await db.email_logs.find({}, {"_id": 0}).sort("sent_at", -1).limit(200).to_list(200)
    return logs

@api_router.post("/emails/resend/{email_id}")
async def resend_email(email_id: str, user: dict = Depends(get_current_user)):
    # Get original email
    email = await db.email_logs.find_one({"id": email_id})
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Resend
    success = await send_email(
        email["to_email"],
        email["subject"],
        email["body"],
        email["email_type"]
    )
    
    if success:
        return {"message": "Email resent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to resend email")

@api_router.post("/support/message")
async def submit_support_message(data: SupportMessage):
    # Store support message
    message_id = str(uuid.uuid4())
    message_doc = {
        "id": message_id,
        "name": data.name,
        "email": data.email,
        "subject": data.subject,
        "message": data.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "new"
    }
    await db.support_messages.insert_one(message_doc)
    
    # Send notification email to support
    support_email = os.environ.get('SUPPORT_EMAIL', 'support@eagenerator.com')
    subject = f"New Support Message: {data.subject}"
    body = f"""
    <h2>New Support Message</h2>
    <p><strong>From:</strong> {data.name} ({data.email})</p>
    <p><strong>Subject:</strong> {data.subject}</p>
    <p><strong>Message:</strong></p>
    <p>{data.message}</p>
    """
    
    await send_email(support_email, subject, body, "support")
    
    return {"message": "Support message submitted successfully", "id": message_id}

@api_router.get("/support/messages")
async def get_support_messages(user: dict = Depends(get_current_user)):
    # Get all support messages
    messages = await db.support_messages.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return messages

# Admin Endpoints
async def check_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@api_router.get("/admin/users")
async def get_all_users(admin: dict = Depends(check_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).sort("created_at", -1).to_list(1000)
    return users

@api_router.put("/admin/users/{user_id}/approve")
async def approve_user(user_id: str, admin: dict = Depends(check_admin)):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": "active"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User approved successfully"}

@api_router.put("/admin/users/{user_id}/reject")
async def reject_user(user_id: str, admin: dict = Depends(check_admin)):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User rejected and removed"}

@api_router.put("/admin/users/{user_id}/suspend")
async def suspend_user(user_id: str, admin: dict = Depends(check_admin)):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": "suspended"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User suspended successfully"}

@api_router.put("/admin/users/{user_id}/activate")
async def activate_user(user_id: str, admin: dict = Depends(check_admin)):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": "active"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User activated successfully"}

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(check_admin)):
    # Delete user and all their data
    await db.users.delete_one({"id": user_id})
    await db.expert_advisors.delete_many({"user_id": user_id})
    await db.license_assignments.delete_many({"ea_id": {"$in": [ea["id"] for ea in await db.expert_advisors.find({"user_id": user_id}).to_list(1000)]}})
    await db.mt5_accounts.delete_many({"user_id": user_id})
    return {"message": "User and all associated data deleted"}

@api_router.get("/admin/analytics")
async def get_admin_analytics(admin: dict = Depends(check_admin)):
    total_users = await db.users.count_documents({})
    pending_users = await db.users.count_documents({"status": "pending"})
    active_users = await db.users.count_documents({"status": "active"})
    suspended_users = await db.users.count_documents({"status": "suspended"})
    
    total_eas = await db.expert_advisors.count_documents({})
    total_licenses = await db.license_assignments.count_documents({})
    
    # Calculate total revenue
    licenses = await db.license_assignments.find({}, {"_id": 0}).to_list(10000)
    total_revenue = sum([l.get("purchase_amount", 0) for l in licenses if l.get("purchase_amount")])
    
    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "active_users": active_users,
        "suspended_users": suspended_users,
        "total_eas": total_eas,
        "total_licenses": total_licenses,
        "total_revenue": total_revenue
    }

@api_router.get("/admin/user/{user_id}/activity")
async def get_user_activity(user_id: str, admin: dict = Depends(check_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    eas = await db.expert_advisors.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    # Get licenses for all user's EAs
    ea_ids = [ea["id"] for ea in eas]
    licenses = await db.license_assignments.find({"ea_id": {"$in": ea_ids}}, {"_id": 0}).to_list(1000)
    
    return {
        "user": user,
        "eas": eas,
        "licenses": licenses,
        "ea_count": len(eas),
        "license_count": len(licenses)
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