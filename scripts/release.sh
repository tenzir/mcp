#!/usr/bin/env bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Files containing version
PYPROJECT_FILE="pyproject.toml"
INIT_FILE="src/tenzir_mcp/__init__.py"

# Function to print colored output
print_info() { echo -e "${GREEN}►${NC} $1"; }
print_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_header() { echo -e "\n${BOLD}$1${NC}\n"; }

# Function to get current version from pyproject.toml
get_current_version() {
    grep '^version = ' "$PYPROJECT_FILE" | sed 's/version = "\(.*\)"/\1/'
}

# Function to parse semantic version
parse_version() {
    local version=$1
    IFS='.' read -r major minor patch <<< "$version"
    echo "$major $minor $patch"
}

# Function to bump version based on type
bump_version() {
    local current=$1
    local bump_type=$2
    
    read -r major minor patch <<< "$(parse_version "$current")"
    
    case "$bump_type" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
    esac
    
    echo "${major}.${minor}.${patch}"
}

# Function to update version in files
update_version() {
    local old_version=$1
    local new_version=$2
    
    # Update pyproject.toml
    sed -i.bak "s/version = \"${old_version}\"/version = \"${new_version}\"/" "$PYPROJECT_FILE"
    rm "${PYPROJECT_FILE}.bak"
    
    # Update __init__.py
    sed -i.bak "s/__version__ = \"${old_version}\"/__version__ = \"${new_version}\"/" "$INIT_FILE"
    rm "${INIT_FILE}.bak"
}

# Function to check if working directory is clean
check_working_directory() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Working directory is not clean. Please commit or stash changes first."
        exit 1
    fi
}

# Function to check if on main branch
check_branch() {
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        print_warn "Not on main branch (currently on: $current_branch)"
        echo "It's recommended to release from the main branch."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
}

# Function to select release type interactively
select_release_type() {
    print_header "Select Release Type"
    echo "Current version: ${BOLD}$1${NC}"
    echo ""
    echo "  ${BOLD}1)${NC} Patch ($(bump_version "$1" patch)) - Bug fixes and small changes"
    echo "  ${BOLD}2)${NC} Minor ($(bump_version "$1" minor)) - New features (backwards-compatible)"
    echo "  ${BOLD}3)${NC} Major ($(bump_version "$1" major)) - Breaking changes"
    echo ""
    
    local choice
    while true; do
        read -p "Select release type (1-3): " -n 1 -r choice
        echo
        case $choice in
            1) echo "patch"; break ;;
            2) echo "minor"; break ;;
            3) echo "major"; break ;;
            *) print_error "Invalid choice. Please select 1, 2, or 3." ;;
        esac
    done
}

# Function to display changes since last release
show_changes() {
    local previous_tag=$1
    local comparison_ref=${2:-HEAD}
    
    print_header "Changes Since Last Release"
    
    if [[ -n "$previous_tag" ]]; then
        echo "Comparing: ${BOLD}$previous_tag${NC} → ${BOLD}$comparison_ref${NC}"
        echo ""
        
        # Get commit count
        local commit_count
        commit_count=$(git rev-list --count "$previous_tag..$comparison_ref")
        echo "📊 ${BOLD}$commit_count${NC} commits since $previous_tag"
        echo ""
        
        # Show commits with format
        echo "${BOLD}Commits:${NC}"
        git log --pretty=format:"  ${GREEN}•${NC} %s ${BLUE}(%h)${NC}" "$previous_tag..$comparison_ref" | head -20
        
        if [[ $commit_count -gt 20 ]]; then
            echo ""
            echo "  ... and $((commit_count - 20)) more"
        fi
        
        # Show file statistics
        echo ""
        echo ""
        echo "${BOLD}Files changed:${NC}"
        git diff --stat "$previous_tag..$comparison_ref" | tail -1
    else
        echo "This will be the first release!"
        echo ""
        local commit_count
        commit_count=$(git rev-list --count HEAD)
        echo "📊 ${BOLD}$commit_count${NC} total commits"
        echo ""
        
        echo "${BOLD}Recent commits:${NC}"
        git log --pretty=format:"  ${GREEN}•${NC} %s ${BLUE}(%h)${NC}" HEAD | head -10
        echo ""
        echo "  ... and more"
    fi
}

# Function to create GitHub release URL with pre-filled data
get_github_release_url() {
    local version=$1
    local previous_tag=$2
    
    # URL encode the release notes
    local title="v${version}"
    local body="## What's Changed%0A%0A"
    
    if [[ -n "$previous_tag" ]]; then
        body="${body}**Full Changelog**: https://github.com/tenzir/mcp/compare/${previous_tag}...v${version}"
    else
        body="${body}Initial release"
    fi
    
    echo "https://github.com/tenzir/mcp/releases/new?tag=v${version}&title=${title}&body=${body}"
}

# Main script
main() {
    # Parse command line arguments
    local dry_run=false
    if [[ $# -gt 0 ]] && [[ "$1" == "--dry-run" ]]; then
        dry_run=true
        print_warn "DRY RUN MODE - No changes will be made"
    fi
    
    # Check prerequisites
    if [[ "$dry_run" == false ]]; then
        check_working_directory
        check_branch
    fi
    
    # Get current version
    current_version=$(get_current_version)
    
    # Interactive selection if no type specified
    bump_type=$(select_release_type "$current_version")
    
    # Calculate new version
    new_version=$(bump_version "$current_version" "$bump_type")
    
    # Get previous tag
    previous_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    
    # Show what changed
    show_changes "$previous_tag"
    
    # Show release summary
    print_header "Release Summary"
    echo "  📌 Type:    ${BOLD}$bump_type${NC}"
    echo "  📦 Version: ${BOLD}$current_version${NC} → ${BOLD}$new_version${NC}"
    echo "  🏷️  Tag:     ${BOLD}v$new_version${NC}"
    echo ""
    echo "This will:"
    echo "  1. Update version in pyproject.toml and __init__.py"
    echo "  2. Run pre-release checks (make check)"
    echo "  3. Commit and tag as v$new_version"
    echo "  4. Push to GitHub"
    echo "  5. Open GitHub release page in your browser"
    
    # Confirm
    echo ""
    read -p "$(echo -e "${BOLD}Proceed with release?${NC} (y/N): ")" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Release cancelled"
        exit 0
    fi
    
    if [[ "$dry_run" == false ]]; then
        # Update version in files
        print_info "Updating version to $new_version..."
        update_version "$current_version" "$new_version"
        
        # Run checks
        print_info "Running pre-release checks..."
        if ! make check; then
            print_error "Pre-release checks failed. Rolling back changes..."
            git checkout -- "$PYPROJECT_FILE" "$INIT_FILE"
            exit 1
        fi
        
        # Commit changes
        print_info "Committing version bump..."
        git add "$PYPROJECT_FILE" "$INIT_FILE"
        git commit -m "Release v$new_version"
        
        # Create tag
        print_info "Creating tag v$new_version..."
        git tag "v$new_version"
        
        # Push to origin
        print_info "Pushing to GitHub..."
        git push origin main
        git push origin "v$new_version"
        
        # Success!
        echo ""
        print_info "${GREEN}✓ Release v$new_version pushed successfully!${NC}"
        
        # Get the GitHub release URL
        release_url=$(get_github_release_url "$new_version" "$previous_tag")
        
        # Open browser
        echo ""
        print_info "Opening GitHub release page..."
        if command -v open &> /dev/null; then
            open "$release_url"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$release_url"
        else
            echo "Please open this URL in your browser:"
            echo "$release_url"
        fi
        
        echo ""
        echo "📝 Next: Add detailed release notes in the browser and click 'Publish release'"
        echo ""
        echo "After publishing, verify with:"
        echo "  uvx tenzir-mcp@latest --version"
        echo "  docker pull ghcr.io/tenzir/mcp:latest"
    else
        print_info "[DRY RUN] Would update version to $new_version"
        print_info "[DRY RUN] Would run: make check"
        print_info "[DRY RUN] Would commit: Release v$new_version"
        print_info "[DRY RUN] Would create tag: v$new_version"
        print_info "[DRY RUN] Would push to GitHub"
        print_info "[DRY RUN] Would open browser to GitHub release page"
    fi
}

# Run main function
main "$@"