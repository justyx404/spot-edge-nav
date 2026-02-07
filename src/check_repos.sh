#!/bin/bash
# Check the status of all git repos in the src directory
# Usage: ./check_repos.sh [--fetch]
#   --fetch    Fetch from remote before comparing (requires network)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FETCH=false

if [[ "$1" == "--fetch" ]]; then
    FETCH=true
fi

# Repos to skip
IGNORE_REPOS=("ocs2" "elevation_mapping_cupy" "ocs2_robotic_assets" "velodyne")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "======================================"
echo " Git Repo Status Check"
echo "======================================"
echo ""

for dir in "$SCRIPT_DIR"/*/; do
    if [ ! -d "$dir/.git" ]; then
        continue
    fi

    repo_name=$(basename "$dir")

    # Skip ignored repos
    for ignore in "${IGNORE_REPOS[@]}"; do
        if [[ "$repo_name" == "$ignore" ]]; then
            continue 2
        fi
    done

    branch=$(git -C "$dir" branch --show-current 2>/dev/null)
    
    if $FETCH; then
        git -C "$dir" fetch --quiet 2>/dev/null
    fi

    # Check for uncommitted changes
    has_changes=false
    has_staged=false
    has_untracked=false

    if ! git -C "$dir" diff --quiet 2>/dev/null; then
        has_changes=true
    fi
    if ! git -C "$dir" diff --cached --quiet 2>/dev/null; then
        has_staged=true
    fi
    if [ -n "$(git -C "$dir" ls-files --others --exclude-standard 2>/dev/null)" ]; then
        has_untracked=true
    fi

    # Check ahead/behind remote
    upstream=$(git -C "$dir" rev-parse --abbrev-ref "@{upstream}" 2>/dev/null)
    ahead=0
    behind=0
    if [ -n "$upstream" ]; then
        ahead=$(git -C "$dir" rev-list --count "$upstream..HEAD" 2>/dev/null || echo 0)
        behind=$(git -C "$dir" rev-list --count "HEAD..$upstream" 2>/dev/null || echo 0)
    fi

    # Determine overall status
    status_icon="${GREEN}✔${NC}"
    status_details=""

    if $has_staged; then
        status_icon="${YELLOW}●${NC}"
        status_details+=" ${YELLOW}staged changes${NC}"
    fi
    if $has_changes; then
        status_icon="${YELLOW}●${NC}"
        status_details+=" ${YELLOW}unstaged changes${NC}"
    fi
    if $has_untracked; then
        status_icon="${YELLOW}●${NC}"
        status_details+=" ${YELLOW}untracked files${NC}"
    fi
    if [ "$behind" -gt 0 ]; then
        status_icon="${RED}✘${NC}"
        status_details+=" ${RED}↓${behind} behind${NC}"
    fi
    if [ "$ahead" -gt 0 ]; then
        status_details+=" ${CYAN}↑${ahead} ahead${NC}"
    fi
    if [ -z "$upstream" ]; then
        status_details+=" ${YELLOW}(no upstream)${NC}"
    fi

    printf " ${status_icon}  %-30s ${CYAN}%-15s${NC}%b\n" "$repo_name" "($branch)" "$status_details"
done

echo ""
echo "--------------------------------------"
echo "Legend: ${GREEN}✔${NC} up-to-date  ${YELLOW}●${NC} local changes  ${RED}✘${NC} behind remote"
if ! $FETCH; then
    echo ""
    echo "Tip: Run with --fetch to check against latest remote state"
fi
