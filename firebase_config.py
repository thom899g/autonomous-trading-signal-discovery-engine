"""
Firebase configuration and state management for the trading ecosystem.
Critical for maintaining persistent state across system restarts.
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)

class FirebaseManager:
    """Singleton manager for Firebase Firestore operations"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.db = None
        self.initialized = False
        self._initialized = True
        
    def initialize(self, project_id: str, credentials_path: str) -> bool:
        """
        Initialize Firebase connection with error handling
        
        Args:
            project_id: Firebase project ID
            credentials_path: Path to service account JSON
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if not os.path.exists(credentials_path):
                logger.error(f"Firebase credentials not found at: {credentials_path}")
                return False
                
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
            
            self.db = firestore.client()
            self.initialized = True
            logger.info(f"Firebase initialized successfully for project: {project_id}")
            return True
            
        except FirebaseError as e:
            logger.error(f"Firebase initialization failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Firebase init: {str(e)}")
            return False
    
    def save_state(self, 
                   collection: str, 
                   doc_id: str, 
                   data: Dict[str, Any],
                   merge: bool = True) -> bool:
        """
        Save state to Firestore with timestamp
        
        Args:
            collection: Collection name
            doc_id: Document ID
            data: Data to save
            merge: Whether to merge with existing data
            
        Returns:
            bool: True if successful
        """
        if not self.initialized or not self.db:
            logger.error("Firebase not initialized")
            return False
            
        try:
            # Add metadata
            data_with_meta = {
                **data,
                '_updated_at': datetime.utcnow().isoformat(),
                '_system_version': '1.0.0'
            }
            
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(data_with_meta, merge=merge)
            logger.debug(f"Saved state to {collection}/{doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")
            return False
    
    def load_state(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Load state from Firestore
        
        Args:
            collection: Collection name
            doc_id: Document ID
            
        Returns:
            Optional[Dict]: State data or None
        """
        if not self.initialized or not self.db:
            logger.error("Firebase not initialized")
            return None
            
        try:
            doc