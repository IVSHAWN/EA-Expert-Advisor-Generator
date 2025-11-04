# AI-Powered Expert Advisor Generator for MT5

A professional trading application that generates MetaTrader 5 Expert Advisors and Indicators using AI (GPT-4o), with license management and bot control features.

## Features

### 1. **AI-Powered EA Generation**
- Describe your trading strategy in plain English
- GPT-4o generates production-ready MQL5 code
- Support for both Expert Advisors (EA) and Indicators
- Automatic license key generation for each EA

### 2. **License Management**
- Unique license keys for each generated EA
- Subscription-based licensing system
- Secure key validation

### 3. **MT5 Integration**
- Connect multiple MetaTrader 5 accounts
- Store account credentials securely
- Real-time account status monitoring

### 4. **Bot Control Dashboard**
- Activate/deactivate bots remotely
- Visual status indicators
- Bot status stored in database for MT5 EA to poll

### 5. **Beautiful Modern UI**
- Futuristic purple/blue gradient theme
- Trading dashboard background with candlestick aesthetics
- Glass-morphism effects
- Responsive design

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - Database for users, EAs, licenses, MT5 accounts
- **emergentintegrations** - AI integration library with Emergent LLM key
- **OpenAI GPT-4o** - For generating MQL5 code
- **JWT Authentication** - Secure user authentication
- **bcrypt** - Password hashing

### Frontend
- **React 19** - UI framework
- **Tailwind CSS** - Styling
- **Shadcn/UI** - Component library
- **Axios** - API calls
- **React Router** - Navigation
- **Sonner** - Toast notifications

## How It Works

### EA Generation Flow
1. User describes their trading strategy
2. Backend sends prompt to GPT-4o via emergentintegrations
3. GPT-4o generates complete MQL5 code
4. System creates license key and stores EA in database
5. User can view code, download .mq5 file, or copy license key

### Bot Control System
- Bot status stored in MongoDB
- MT5 EA (custom code needed) polls `/api/bot/status/{ea_id}` endpoint
- When user toggles bot in dashboard, status updates in database
- MT5 EA reads new status and enables/disables trading logic

### MT5 Account Connection
- Users input account number, server, and password
- Credentials stored in database
- Used for tracking which accounts are using which EAs

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - Login and get JWT token

### EA Management
- `POST /api/ea/generate` - Generate new EA/Indicator
- `GET /api/ea/list` - List user's EAs
- `GET /api/ea/{ea_id}` - Get specific EA details

### MT5 Accounts
- `POST /api/mt5/connect` - Connect MT5 account
- `GET /api/mt5/accounts` - List connected accounts

### Bot Control
- `POST /api/bot/toggle` - Activate/deactivate bot
- `GET /api/bot/status/{ea_id}` - Get bot status

## Usage Guide

1. **Register/Login**: Create an account or sign in
2. **Generate EA**: 
   - Select type (EA or Indicator)
   - Describe your strategy
   - Add optional details (stop loss, take profit, etc.)
   - Click Generate
3. **View EAs**: Check "My EAs" tab to see generated advisors
4. **Download Code**: Click "Download" to get .mq5 file
5. **Get License**: Copy license key for distribution
6. **Connect MT5**: Add your trading account credentials
7. **Control Bot**: Toggle switch to activate/deactivate

## MT5 EA Integration

To use the bot control feature, your MT5 EA should poll the API:

```mql5
// Poll the API endpoint every few seconds
string apiUrl = "https://your-domain.com/api/bot/status/YOUR_EA_ID";
string response = WebRequest("GET", apiUrl, "", 5000, result, headers);

// Parse JSON response and check is_active
if (is_active == true) {
    // Execute trading logic
} else {
    // Pause trading
}
```
