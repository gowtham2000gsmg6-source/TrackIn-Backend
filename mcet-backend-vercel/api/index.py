import os
import sys

# Vercel's Python runtime executes this file directly, so the project root
# (one level up, where main.py / database.py / models.py / routes/ live)
# needs to be on sys.path for the existing flat imports (`import models`,
# `from database import ...`) to keep working unchanged.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402

# Vercel's @vercel/python builder looks for a top-level ASGI/WSGI `app`
# object in this file - nothing else to do here.
