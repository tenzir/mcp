#!/usr/bin/env bash

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root (parent of scripts directory)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors for output - using actual escape characters
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
BOLD=$'\033[1m'
NC=$'\033[0m' # No Color

# Files containing version
PYPROJECT_FILE="pyproject.toml"
INIT_FILE="src/tenzir_mcp/__init__.py"

# Function to print colored output
print_info() { printf "${GREEN}►${NC} %s\n" "$1"; }
print_warn() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
print_error() { printf "${RED}✗${NC} %s\n" "$1"; }
print_header() { printf "\n${BOLD}%s${NC}\n\n" "$1"; }

# Functions to print to stderr (for interactive prompts)
print_header_stderr() { printf "\n${BOLD}%s${NC}\n\n" "$1" >&2; }
print_error_stderr() { printf "${RED}✗${NC} %s\n" "$1" >&2; }

# Function to get current version from pyproject.toml
get_current_version() {
    if [[ ! -f "$PYPROJECT_FILE" ]]; then
        print_error "Cannot find $PYPROJECT_FILE in $(pwd)"
        exit 1
    fi
    grep '^version = ' "$PYPROJECT_FILE" | sed 's/version = "\(.*\)"/\1/'
}

# Function to parse semantic version
parse_version() {
    local version=$1
    local IFS='.'
    read -r major minor patch <<< "$version"
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
        printf "It's recommended to release from the main branch.\n"
        printf "Continue anyway? (y/N): "
        read -n 1 -r
        printf "\n"
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
}

# Function to select release type interactively
select_release_type() {
    print_header_stderr "Select Release Type"
    printf "Current version: ${BOLD}%s${NC}\n" "$1" >&2
    printf "\n" >&2
    printf "  ${BOLD}1)${NC} Patch (%s) - Bug fixes and small changes\n" "$(bump_version "$1" patch)" >&2
    printf "  ${BOLD}2)${NC} Minor (%s) - New features (backwards-compatible)\n" "$(bump_version "$1" minor)" >&2
    printf "  ${BOLD}3)${NC} Major (%s) - Breaking changes\n" "$(bump_version "$1" major)" >&2
    printf "\n" >&2
    
    local choice
    while true; do
        printf "Select release type (1-3): " >&2
        read -n 1 -r choice
        echo >&2
        case $choice in
            1) echo "patch"; break ;;
            2) echo "minor"; break ;;
            3) echo "major"; break ;;
            *) print_error_stderr "Invalid choice. Please select 1, 2, or 3." ;;
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
    printf "  📌 Type:    ${BOLD}%s${NC}\n" "$bump_type"
    printf "  📦 Version: ${BOLD}%s${NC} → ${BOLD}%s${NC}\n" "$current_version" "$new_version"
    printf "  🏷️  Tag:     ${BOLD}v%s${NC}\n" "$new_version"
    printf "\n"
    printf "This will:\n"
    printf "  1. Update version in pyproject.toml and __init__.py\n"
    printf "  2. Run pre-release checks (make check)\n"
    printf "  3. Create a release branch and PR\n"
    printf "  4. Auto-merge PR, create tag, and draft GitHub release\n"
    printf "  5. Open browser for you to edit and publish release notes\n"
    
    # Confirm
    printf "\n"
    printf "${BOLD}Proceed with release?${NC} (y/N): "
    read -n 1 -r
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
        
        # Create release branch
        local release_branch="release-v$new_version"
        print_info "Creating release branch $release_branch..."
        git checkout -b "$release_branch"
        
        # Commit changes
        print_info "Committing version bump..."
        git add "$PYPROJECT_FILE" "$INIT_FILE"
        git commit -m "Release v$new_version"
        
        # Push branch
        print_info "Pushing branch to GitHub..."
        git push -u origin "$release_branch"
        
        # Create PR using GitHub CLI
        print_info "Creating pull request..."
        if command -v gh &> /dev/null; then
            pr_url=$(gh pr create \
                --title "Release v$new_version" \
                --body "Automated version bump for release v$new_version" \
                --base main \
                --head "$release_branch")
            
            printf "\n"
            printf "${GREEN}✓ Pull request created!${NC}\n"
            printf "PR: %s\n" "$pr_url"
            
            # Wait for PR to be ready
            print_info "Waiting for PR checks..."
            if gh pr checks "$pr_url" --watch; then
                # Auto-merge if checks pass
                print_info "Checks passed! Merging PR..."
                gh pr merge "$pr_url" --squash --auto --delete-branch
                
                # Wait for merge
                print_info "Waiting for PR to merge..."
                while gh pr view "$pr_url" --json state -q .state | grep -q "OPEN"; do
                    sleep 2
                done
                
                # Switch back to main and pull
                print_info "PR merged! Switching to main..."
                git checkout main
                git pull origin main
                
                # Create and push tag
                print_info "Creating and pushing tag v$new_version..."
                git tag "v$new_version"
                git push origin "v$new_version"
                
                # Create draft GitHub release with auto-generated notes
                print_info "Creating draft GitHub release..."
                gh release create "v$new_version" \
                    --draft \
                    --title "v$new_version" \
                    --generate-notes \
                    --notes-start-tag "${previous_tag:-$(git rev-list --max-parents=0 HEAD)}"
                
                # Get the release URL
                release_url="https://github.com/tenzir/mcp/releases/edit/v$new_version"
                
                printf "\n"
                printf "${GREEN}✓ Draft release created!${NC}\n"
                printf "\n"
                print_info "Opening browser to edit and publish release..."
                if command -v open &> /dev/null; then
                    open "$release_url"
                elif command -v xdg-open &> /dev/null; then
                    xdg-open "$release_url"
                else
                    printf "Please open this URL to edit and publish the release:\n"
                    printf "%s\n" "$release_url"
                fi
                
                printf "\n"
                printf "📝 ${YELLOW}Next steps:${NC}\n"
                printf "  1. Review the auto-generated release notes\n"
                printf "  2. Edit as needed (add highlights, breaking changes, etc.)\n"
                printf "  3. Click 'Publish release' when ready\n"
                printf "\n"
                printf "After publishing, verify with:\n"
                printf "  uvx tenzir-mcp@latest --version\n"
                printf "  docker pull ghcr.io/tenzir/mcp:latest\n"
            else
                print_error "PR checks failed! Please review and fix."
                printf "PR: %s\n" "$pr_url"
                exit 1
            fi
        else
            print_warn "GitHub CLI (gh) not found. Please install it:"
            printf "  brew install gh\n"
            exit 1
        fi
    else
        print_info "[DRY RUN] Would update version to $new_version"
        print_info "[DRY RUN] Would run: make check"
        print_info "[DRY RUN] Would create branch: release-v$new_version"
        print_info "[DRY RUN] Would commit: Release v$new_version"
        print_info "[DRY RUN] Would create PR and wait for checks"
        print_info "[DRY RUN] Would auto-merge PR after checks pass"
        print_info "[DRY RUN] Would create tag: v$new_version"
        print_info "[DRY RUN] Would create draft GitHub release"
        print_info "[DRY RUN] Would open browser to edit release notes"
    fi
}

# Run main function
main "$@"