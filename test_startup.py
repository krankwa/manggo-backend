#!/usr/bin/env python
"""Test script to verify Railway deployment can start"""
import os
import sys

print("=" * 50)
print("STARTUP TEST")
print("=" * 50)

# Test 1: Python version
print(f"✓ Python version: {sys.version}")

# Test 2: Django import
try:
    import django
    print(f"✓ Django version: {django.get_version()}")
except ImportError as e:
    print(f"✗ Django import failed: {e}")
    sys.exit(1)

# Test 3: Settings
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mangoAPI.settings')
    django.setup()
    print("✓ Django settings loaded")
except Exception as e:
    print(f"✗ Django setup failed: {e}")
    sys.exit(1)

# Test 4: Database
try:
    from django.db import connection
    connection.ensure_connection()
    print("✓ Database connection OK")
except Exception as e:
    print(f"✗ Database connection failed: {e}")

# Test 5: TensorFlow
try:
    import tensorflow as tf
    print(f"✓ TensorFlow version: {tf.__version__}")
except ImportError as e:
    print(f"✗ TensorFlow import failed: {e}")
    sys.exit(1)

# Test 6: Model files
try:
    from django.conf import settings
    leaf_model = os.path.join(settings.BASE_DIR, 'models', 'leaf-mobilenetv2.keras')
    fruit_model = os.path.join(settings.BASE_DIR, 'models', 'fruit-mobilenetv2.keras')
    
    if os.path.exists(leaf_model):
        size_mb = os.path.getsize(leaf_model) / (1024 * 1024)
        print(f"✓ Leaf model found: {size_mb:.2f} MB")
    else:
        print(f"✗ Leaf model NOT found at: {leaf_model}")
    
    if os.path.exists(fruit_model):
        size_mb = os.path.getsize(fruit_model) / (1024 * 1024)
        print(f"✓ Fruit model found: {size_mb:.2f} MB")
    else:
        print(f"✗ Fruit model NOT found at: {fruit_model}")
except Exception as e:
    print(f"✗ Model check failed: {e}")

# Test 7: Memory available
try:
    import psutil
    mem = psutil.virtual_memory()
    print(f"✓ Memory available: {mem.available / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB")
except ImportError:
    print("⚠ psutil not installed, cannot check memory")

print("=" * 50)
print("STARTUP TEST COMPLETE")
print("=" * 50)
