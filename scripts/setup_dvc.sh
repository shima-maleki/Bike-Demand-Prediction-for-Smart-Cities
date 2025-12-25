#!/bin/bash
# DVC Setup Script
# Initialize DVC for data and model versioning

set -e

echo "========================================="
echo "DVC Setup Script"
echo "========================================="

# Check if DVC is installed
if ! command -v dvc &> /dev/null; then
    echo "Error: DVC is not installed. Installing..."
    pip install dvc dvc-s3
fi

# Initialize DVC
echo "Initializing DVC..."
dvc init

# Configure DVC
echo "Configuring DVC..."
dvc config core.autostage true

# Add remote storage (update this based on your storage choice)
echo ""
echo "Select remote storage option:"
echo "1. S3 (AWS)"
echo "2. Google Drive"
echo "3. Local directory"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        read -p "Enter S3 bucket name: " bucket
        read -p "Enter AWS region (default: us-east-1): " region
        region=${region:-us-east-1}
        dvc remote add -d origin s3://$bucket/dvc-storage
        dvc remote modify origin region $region
        echo "S3 remote configured. Make sure AWS credentials are set."
        ;;
    2)
        read -p "Enter Google Drive folder ID: " folder_id
        dvc remote add -d origin gdrive://$folder_id
        echo "Google Drive remote configured."
        ;;
    3)
        read -p "Enter local directory path: " local_path
        dvc remote add -d origin $local_path
        echo "Local remote configured at: $local_path"
        ;;
    *)
        echo "Invalid choice. Skipping remote configuration."
        ;;
esac

# Track data directories with DVC
echo ""
echo "Setting up DVC tracking for data and models..."

# Track data directory
if [ -d "data/raw" ]; then
    echo "Tracking data/raw..."
    dvc add data/raw
fi

if [ -d "data/processed" ]; then
    echo "Tracking data/processed..."
    dvc add data/processed
fi

# Track models directory
if [ -d "models" ]; then
    echo "Tracking models..."
    dvc add models
fi

# Git add DVC files
echo ""
echo "Adding DVC files to git..."
git add .dvc .dvcignore
git add data/.gitignore models/.gitignore 2>/dev/null || true

echo ""
echo "========================================="
echo "DVC setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Commit DVC files: git commit -m 'Initialize DVC'"
echo "2. Push data to remote: dvc push"
echo "3. Track changes: dvc add <file/directory>"
echo ""
echo "Useful DVC commands:"
echo "  dvc add <file>       - Track file with DVC"
echo "  dvc push             - Push data to remote storage"
echo "  dvc pull             - Pull data from remote storage"
echo "  dvc status           - Check DVC status"
echo "  dvc repro            - Reproduce pipeline"
echo ""
