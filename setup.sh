#!/bin/bash

# Color codes for pretty output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting think-before-share Project Setup ===${NC}"

# Function to check command availability
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: Required tool '$1' is not installed.${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Found $1: $($1 --version | head -n 1)${NC}"
        return 0
    fi
}

# 1. Check for required tools
echo -e "\n${BLUE}[1/5] Checking system prerequisites...${NC}"
FAILED=0
check_command "node" || FAILED=1
check_command "python3" || FAILED=1

# Check for pip/pip3
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓ Found pip3: $(pip3 --version | head -n 1)${NC}"
elif command -v pip &> /dev/null; then
    echo -e "${GREEN}✓ Found pip: $(pip --version | head -n 1)${NC}"
else
    echo -e "${RED}Error: Neither pip3 nor pip was found on your system.${NC}"
    FAILED=1
fi

if [ $FAILED -ne 0 ]; then
    echo -e "\n${RED}Setup failed. Please install the missing tools and try again.${NC}"
    exit 1
fi

# 2. Set up Backend Python Virtual Environment
echo -e "\n${BLUE}[2/5] Setting up backend Python virtual environment...${NC}"
mkdir -p backend
cd backend

if [ ! -d ".venv" ]; then
    echo -e "Creating virtual environment in backend/.venv..."
    python3 -m venv .venv
else
    echo -e "Virtual environment backend/.venv already exists."
fi

# Activate virtual environment and install packages
echo -e "Activating virtual environment and installing packages..."
source .venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${YELLOW}Warning: requirements.txt not found. Installing packages individually...${NC}"
    pip install fastapi uvicorn youtube-transcript-api tavily-python google-generativeai pydantic python-dotenv
fi

cd ..
echo -e "${GREEN}✓ Backend environment set up successfully.${NC}"

# 3. Set up Next.js Frontend
echo -e "\n${BLUE}[3/5] Setting up Next.js frontend...${NC}"
if [ ! -d "frontend" ]; then
    echo -e "Bootstrapping Next.js app in frontend/ folder..."
    npx create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
else
    echo -e "frontend directory already exists. Skipping create-next-app."
fi

# 4. Set up shadcn/ui in Frontend
echo -e "\n${BLUE}[4/5] Initializing shadcn/ui in frontend...${NC}"
cd frontend
if [ -f "package.json" ]; then
    echo -e "Running shadcn/ui init..."
    # Run non-interactively using defaults
    npx shadcn@latest init --defaults --yes
    
    # Install additional common components that will be useful for a premium UI
    echo -e "Installing common UI packages (lucide-react)..."
    npm install lucide-react
else
    echo -e "${RED}Error: frontend package.json not found. Failed to init shadcn/ui.${NC}"
    exit 1
fi
cd ..

# 5. Configure environment variables
echo -e "\n${BLUE}[5/5] Configuring environment files...${NC}"
if [ -f ".env.example" ]; then
    # Copy env example to backend and frontend local env files if they don't exist
    if [ ! -f "backend/.env" ]; then
        cp .env.example backend/.env
        echo -e "${GREEN}✓ Created backend/.env${NC}"
    else
        echo -e "backend/.env already exists."
    fi

    if [ ! -f "frontend/.env.local" ]; then
        cp .env.example frontend/.env.local
        echo -e "${GREEN}✓ Created frontend/.env.local${NC}"
    else
        echo -e "frontend/.env.local already exists."
    fi
else
    echo -e "${YELLOW}Warning: .env.example not found in root.${NC}"
fi

echo -e "\n${GREEN}=== Setup Completed Successfully! ===${NC}"
echo -e "\n${YELLOW}Next Steps to run the application:${NC}"
echo -e "1. ${BLUE}Configure API Keys:${NC}"
echo -e "   Open ${GREEN}backend/.env${NC} and ${GREEN}frontend/.env.local${NC} and fill in:"
echo -e "   - ${CYAN}GEMINI_API_KEY${NC} (Google Gemini API)"
echo -e "   - ${CYAN}TAVILY_API_KEY${NC} (Tavily Search API)"
echo -e ""
echo -e "2. ${BLUE}Run FastAPI Backend:${NC}"
echo -e "   cd backend"
echo -e "   source .venv/bin/activate"
echo -e "   uvicorn main:app --reload"
echo -e "   (Runs at http://localhost:8000)"
echo -e ""
echo -e "3. ${BLUE}Run Next.js Frontend:${NC}"
echo -e "   cd frontend"
echo -e "   npm run dev"
echo -e "   (Runs at http://localhost:3000)"
echo -e ""
