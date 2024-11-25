import streamlit as st
import requests
from itertools import product
import time
import os
import tempfile
import sqlite3
from scidownl import scihub_download
from PyPDF2 import PdfMerger

# Use temporary directory for file operations in Streamlit Cloud
def get_temp_dir():
    temp_dir = tempfile.mkdtemp()
    # Create a SQLite database in the temp directory for scidownl
    db_path = os.path.join(temp_dir, 'scidownl.db')
    conn = sqlite3.connect(db_path)
    conn.close()
    # Set environment variable for scidownl to use our temporary database
    os.environ['SCIDOWNL_PATH'] = temp_dir
    return temp_dir

# Initialize directories using temp directories for Streamlit Cloud
TEMP_DIR = get_temp_dir()
PAPERS_DIR = os.path.join(TEMP_DIR, "papers")
OUTPUT_DIR = os.path.join(TEMP_DIR, "output")

# Monkey patch scidownl's database path
import scidownl.update_link
scidownl.update_link.PATH = os.path.join(TEMP_DIR, 'scidownl.db')

[... rest of your code remains the same ...]
