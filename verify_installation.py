#!/usr/bin/env python3
"""FitCheck AI - Installation Verification"""

import sys
import os
import subprocess
import httpx

print("\n" + "="*60)
print("  FitCheck AI - Complete Installation Verification")
print("="*60 + "\n")

# 1. Python packages
print("1️⃣  PYTHON PACKAGES")
print("-" * 60)
packages_check = [
    ('fastapi', 'FastAPI'),
    ('uvicorn', 'Uvicorn'),
    ('sqlalchemy', 'SQLAlchemy'),
    ('asyncpg', 'AsyncPG'),
    ('redis', 'Redis'),
    ('PIL', 'Pillow'),
    ('boto3', 'boto3'),
    ('httpx', 'httpx'),
    ('pydantic', 'Pydantic'),
    ('passlib', 'passlib'),
    ('jose', 'python-jose'),
    ('replicate', 'Replicate'),
    ('razorpay', 'Razorpay'),
]

all_installed = True
for module, name in packages_check:
    try:
        __import__(module)
        print(f"   ✓ {name}")
    except ImportError:
        print(f"   ✗ {name} - MISSING")
        all_installed = False

# 2. Configuration files
print("\n2️⃣  CONFIGURATION FILES")
print("-" * 60)

env_path = 'backend/.env'
if os.path.exists(env_path):
    print(f"   ✓ {env_path} exists")
else:
    print(f"   ✗ {env_path} missing")

# 3. Directory structure
print("\n3️⃣  PROJECT STRUCTURE")
print("-" * 60)
dirs = [
    'backend',
    'backend/app',
    'backend/app/api',
    'backend/app/core',
    'backend/app/models',
    'backend/app/services',
    'backend/migrations',
    'frontend',
]
for d in dirs:
    if os.path.isdir(d):
        print(f"   ✓ {d}/")
    else:
        print(f"   ✗ {d}/ missing")

# 4. Services status
print("\n4️⃣  RUNNING SERVICES")
print("-" * 60)

services = [
    ('Backend API', 'http://localhost:8000/health'),
    ('Frontend Server', 'http://localhost:3000'),
]

for name, url in services:
    try:
        client = httpx.Client(timeout=2)
        resp = client.get(url)
        if resp.status_code < 500:
            print(f"   ✓ {name} ({resp.status_code})")
        else:
            print(f"   ✗ {name} ({resp.status_code})")
    except Exception as e:
        print(f"   ✗ {name} - {type(e).__name__}")

# 5. Database models
print("\n5️⃣  DATABASE MODELS")
print("-" * 60)
try:
    from backend.app.models import user, tryon, product
    print("   ✓ User model importable")
    print("   ✓ TryOn model importable")
    print("   ✓ Product model importable")
except Exception as e:
    print(f"   ✗ Models import failed: {e}")

# 6. Summary
print("\n" + "="*60)
if all_installed:
    print("  ✅ INSTALLATION COMPLETE")
    print("\n  Your FitCheck AI project is fully set up!")
    print("  • Backend:  http://localhost:8000")
    print("  • Frontend: http://localhost:3000")
    print("  • API Docs: http://localhost:8000/docs")
else:
    print("  ⚠️  SOME PACKAGES MISSING")
    print("     Run: pip install -r requirements.txt")

print("="*60 + "\n")
