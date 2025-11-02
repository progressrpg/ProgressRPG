#!/bin/bash

set -e

# Check for dry-run flag
dry_run=false
if [[ "$1" == "--dry-run" || "$1" == "-D" ]]; then
  dry_run=true
  echo "🔍 Running in dry-run mode. No changes will be made."
fi

# Get the latest tag, or default to 0.1.0 if none
latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.1.0")
echo "Current version: $latest_tag"

# Parse version
version=${latest_tag#v}
version_number=${version%%-*}  # Gets everything before '-'
suffix=${version#"$version_number"}  # Includes the '-' if present, e.g., '-dev'

IFS='.' read -r major minor patch <<< "$version_number"

# Ask user for bump type
echo "Select version bump:"
select choice in "Patch ($major.$minor.$((patch + 1))$suffix)" \
                  "Minor ($major.$((minor + 1)).0$suffix)" \
                  "Major ($((major + 1)).0.0$suffix)"; do
  case $REPLY in
    1) new_tag="v$major.$minor.$((patch + 1))$suffix"; break ;;
    2) new_tag="v$major.$((minor + 1)).0$suffix"; break ;;
    3) new_tag="v$((major + 1)).0.0$suffix"; break ;;
    *) echo "Invalid choice. Please enter 1, 2 or 3."; continue ;;
  esac
done

# Safety check: does the tag already exist?
if git rev-parse "$new_tag" >/dev/null 2>&1; then
  echo "❗ Tag $new_tag already exists."

  # Try auto-incrementing patch number for patch or minor bumps only
  if [[ "$new_tag" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    base_major="${BASH_REMATCH[1]}"
    base_minor="${BASH_REMATCH[2]}"
    base_patch="${BASH_REMATCH[3]}"

    echo "Trying to find next available patch number..."
    found_new_tag=false
    for ((p=base_patch+1; p<=base_patch+10; p++)); do
      candidate="v${base_major}.${base_minor}.${p}"
      if ! git rev-parse "$candidate" >/dev/null 2>&1; then
        read -p "Use next available tag $candidate? (y/n): " use_candidate
        if [[ "$use_candidate" =~ ^[Yy]$ ]]; then
          new_tag=$candidate
          echo "Using tag $new_tag"
          found_new_tag=true
          break
        fi
      fi
    done

    if ! $found_new_tag; then
      echo "No available patch tags found."
    fi
  fi

  # If tag still exists (didn't pick new one)
  if git rev-parse "$new_tag" >/dev/null 2>&1; then
    read -p "Do you want to DELETE the existing tag $new_tag locally and remotely? (WARNING: This will rewrite history) (y/n): " delete_confirm
    if [[ "$delete_confirm" =~ ^[Yy]$ ]]; then
      echo "Deleting local tag $new_tag..."
      git tag -d "$new_tag"
      echo "Deleting remote tag $new_tag..."
      git push --delete origin "$new_tag"
      echo "Tag $new_tag deleted."
    else
      echo "Aborting due to existing tag."
      exit 1
    fi
  fi
fi

# Confirm
echo "➡️ New tag will be: $new_tag"
read -p "Proceed? (y/n): " confirm
if [[ $confirm != "y" && $confirm != "Y" ]]; then
  echo "❌ Tagging cancelled."
  exit 1
fi

# Get commit messages since last tag
log=$(git log "$latest_tag"..HEAD --pretty=format:"- %s")

# Generate changelog entry
changelog_entry="## $new_tag - $(date +%Y-%m-%d)

$log
"

echo "📝 Generated changelog entry:"
echo "$changelog_entry"

if [[ "$dry_run" = true ]]; then
  echo "✅ Dry run complete. Tag and changelog not written."
  exit 0
fi

# Create Git tag
git tag "$new_tag"
git push origin "$new_tag"

# Prepend changelog entry to CHANGELOG.md (or create file)
if [ -f CHANGELOG.md ]; then
  # Remove existing # Changelog heading (first line), then prepend new entry and add back heading
  tail -n +2 CHANGELOG.md > CHANGELOG.tmp
  echo -e "# Changelog\n\n$changelog_entry$(cat CHANGELOG.tmp)" > CHANGELOG.md
  rm CHANGELOG.tmp
else
  echo -e "# Changelog\n\n$changelog_entry" > CHANGELOG.md
fi

git add CHANGELOG.md
git commit -m "Update changelog for $new_tag"
git push

echo "✅ Tag $new_tag created and CHANGELOG.md updated."
