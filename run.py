#!/usr/bin/env python3
"""
Quick-start launcher for SAR Narrative Generator
Run: python run.py
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "app/main.py",
        "--server.port=8501",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        "--theme.primaryColor=#00205b",
        "--theme.backgroundColor=#ffffff",
        "--theme.secondaryBackgroundColor=#f5f7fb",
        "--theme.textColor=#1a1a2e",
    ]
    print("=" * 60)
    print("  SAR Narrative Generator — Barclays AML Platform")
    print("=" * 60)
    print(f"  Starting on: http://localhost:8501")
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)
    subprocess.run(cmd)
