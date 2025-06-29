# FILE: functions/src/common/database.py
import firebase_admin
from firebase_admin import firestore

# This module initializes the database connection for the entire application.
# It ensures that firebase_admin.initialize_app() is called only once
# and that the db client is a singleton shared across all modules.

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.Client() 