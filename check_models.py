#!/usr/bin/env python3
"""
Script to download model files from a URL or verify they exist
This runs during Docker build to ensure models are present
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / 'models'

def check_model_files():
    """Check if model files exist and are not LFS pointers"""
    models = {
        'leaf-mobilenetv2.keras': MODELS_DIR / 'leaf-mobilenetv2.keras',
        'fruit-mobilenetv2.keras': MODELS_DIR / 'fruit-mobilenetv2.keras'
    }
    
    all_ok = True
    for name, path in models.items():
        if not path.exists():
            print(f"❌ Model file missing: {name}")
            all_ok = False
        else:
            size = path.stat().st_size
            size_mb = size / (1024 * 1024)
            if size < 1000:  # Less than 1KB means it's likely an LFS pointer
                print(f"⚠️  Model file is too small (likely LFS pointer): {name} ({size} bytes)")
                all_ok = False
            else:
                print(f"✅ Model file OK: {name} ({size_mb:.2f} MB)")
    
    return all_ok

if __name__ == '__main__':
    print("=" * 50)
    print("Checking model files...")
    print("=" * 50)
    
    if check_model_files():
        print("\n✅ All model files are present and valid")
        sys.exit(0)
    else:
        print("\n❌ Model files are missing or invalid!")
        print("\nTo fix this:")
        print("1. Run: git lfs pull")
        print("2. Or manually download the model files")
        print("3. Or remove models from Git LFS: git lfs untrack '*.keras'")
        sys.exit(1)
