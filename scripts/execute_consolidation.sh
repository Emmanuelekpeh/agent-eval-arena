#!/bin/bash
# execute_consolidation.sh
# A shell script to execute the complete consolidation process for the AI Battle Arena codebase
# This script runs both the consolidate_codebase.sh and update_imports.py scripts

set -e  # Exit immediately if a command exits with a non-zero status

# ANSI color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}      AI BATTLE ARENA - CODEBASE CONSOLIDATION       ${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Make sure we're in the project root directory
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.."
PROJECT_ROOT=$(pwd)

echo -e "${CYAN}[$(date +%T)]${NC} Starting consolidation process from ${YELLOW}$PROJECT_ROOT${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo -e "${CYAN}[$(date +%T)]${NC} Checking dependencies..."

if ! command_exists python3; then
    echo -e "${RED}ERROR: python3 is required but not installed.${NC}"
    exit 1
fi

# Make scripts executable if they aren't already
echo -e "${CYAN}[$(date +%T)]${NC} Making scripts executable..."
chmod +x scripts/consolidate_codebase.sh
chmod +x scripts/update_imports.py

# Step 1: Run the consolidate_codebase.sh script
echo -e "\n${CYAN}[$(date +%T)]${NC} ${GREEN}Step 1/3:${NC} Running file structure consolidation..."
./scripts/consolidate_codebase.sh

# Check if the consolidation was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: File structure consolidation failed.${NC}"
    exit 1
fi

# Step 2: Run the update_imports.py script
echo -e "\n${CYAN}[$(date +%T)]${NC} ${GREEN}Step 2/3:${NC} Updating import statements..."
python3 ./scripts/update_imports.py .

# Check if the import updates were successful
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Import statement updates failed.${NC}"
    exit 1
fi

# Step 3: Run tests to verify the consolidation
echo -e "\n${CYAN}[$(date +%T)]${NC} ${GREEN}Step 3/3:${NC} Verifying changes..."

# If we have a test command, run it here
if [ -f "tests/run_tests.py" ]; then
    echo -e "${YELLOW}Running test suite...${NC}"
    python3 tests/run_tests.py
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}WARNING: Tests failed after consolidation. Manual review needed.${NC}"
    else
        echo -e "${GREEN}Tests passed successfully!${NC}"
    fi
else
    echo -e "${YELLOW}No test suite found. Skipping verification.${NC}"
fi

# Final summary
echo -e "\n${CYAN}[$(date +%T)]${NC} ${GREEN}Consolidation process complete!${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo -e "${PURPLE}Completed Actions:${NC}"
echo -e "  ${GREEN}✓${NC} Created backup of original files"
echo -e "  ${GREEN}✓${NC} Restructured files into canonical locations"
echo -e "  ${GREEN}✓${NC} Updated import statements across codebase"
echo -e "\n${PURPLE}Next Steps:${NC}"
echo -e "  1. Review the imported_update_report.json file for details on import changes"
echo -e "  2. Check any files with DEPRECATED imports and update or remove them"
echo -e "  3. Manually test the application to ensure it works correctly"
echo -e "${BLUE}=====================================================${NC}" 