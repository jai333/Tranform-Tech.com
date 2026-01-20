"""
Generic API Integration Framework
Supports integration with any third-party API (Bullhorn, LinkedIn, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


class APIConnector(ABC):
    """Abstract base class for API integrations"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize API connector
        
        Args:
            config: Integration configuration with keys:
                - provider: API provider name
                - base_url: Base URL for API
                - auth_type: 'oauth', 'api_key', 'basic'
                - credentials: Dict with auth credentials
                - field_mappings: Dict for field mapping
        """
        self.config = config
        self.provider = config.get('provider', 'unknown')
        self.base_url = config.get('base_url')
        self.auth_type = config.get('auth_type')
        self.credentials = config.get('credentials', {})
        self.field_mappings = config.get('field_mappings', {})
        
        self.session = requests.Session()
        self.last_error = None
        self.last_sync_time = None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the API
        Must be implemented by subclasses
        """
        pass
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Perform GET request
        
        Args:
            endpoint: API endpoint
            params: Query parameters
        
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            headers = self._get_headers()
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GET request failed: {e}")
            self.last_error = str(e)
            raise
    
    def post(self, endpoint: str, data: Dict) -> Dict:
        """
        Perform POST request
        
        Args:
            endpoint: API endpoint
            data: Request payload
        
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            headers = self._get_headers()
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"POST request failed: {e}")
            self.last_error = str(e)
            raise
    
    def put(self, endpoint: str, data: Dict) -> Dict:
        """Perform PUT request"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            headers = self._get_headers()
            response = requests.put(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"PUT request failed: {e}")
            self.last_error = str(e)
            raise
    
    def delete(self, endpoint: str) -> bool:
        """Perform DELETE request"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            headers = self._get_headers()
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE request failed: {e}")
            self.last_error = str(e)
            return False
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self.authenticate()
            logger.info(f"Successfully authenticated with {self.provider}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            self.last_error = str(e)
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers based on auth type"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if self.auth_type == 'api_key':
            api_key = self.credentials.get('api_key')
            headers['Authorization'] = f"Bearer {api_key}"
        
        elif self.auth_type == 'basic':
            username = self.credentials.get('username')
            password = self.credentials.get('password')
            import base64
            creds = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers['Authorization'] = f"Basic {creds}"
        
        return headers
    
    def map_fields(self, external_data: Dict, reverse: bool = False) -> Dict:
        """
        Map fields between external and internal schemas
        
        Args:
            external_data: Data from external API
            reverse: If True, map from internal to external
        
        Returns:
            Mapped data
        """
        mappings = self.field_mappings
        if reverse:
            mappings = {v: k for k, v in mappings.items()}
        
        mapped_data = {}
        for external_key, internal_key in mappings.items():
            if external_key in external_data:
                mapped_data[internal_key] = external_data[external_key]
        
        return mapped_data
    
    def handle_error(self, error: Exception) -> Dict:
        """
        Centralized error handling
        
        Returns:
            Error details dict
        """
        error_details = {
            'provider': self.provider,
            'error_message': str(error),
            'error_type': type(error).__name__,
            'timestamp': datetime.now().isoformat(),
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None
        }
        
        logger.error(f"API Error: {json.dumps(error_details)}")
        return error_details


class BullhornConnector(APIConnector):
    """Bullhorn API Integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://rest.bullhornstaffing.com/rest-services/v1"
        self.oauth_url = "https://auth.bullhornstaffing.com/oauth/authorize"
        self.token_url = "https://auth.bullhornstaffing.com/oauth/token"
    
    def authenticate(self) -> bool:
        """OAuth 2.0 authentication"""
        try:
            # Check if we have a valid token
            if self.credentials.get('access_token'):
                # Test with existing token
                return self._test_token()
            
            # Refresh token if available
            if self.credentials.get('refresh_token'):
                return self._refresh_token()
            
            # Full OAuth flow
            return self._oauth_flow()
        
        except Exception as e:
            logger.error(f"Bullhorn auth failed: {e}")
            self.last_error = str(e)
            return False
    
    def _test_token(self) -> bool:
        """Test if current token is valid"""
        try:
            self.get('login')
            return True
        except:
            return False
    
    def _refresh_token(self) -> bool:
        """Refresh access token"""
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.credentials.get('refresh_token'),
            'client_id': self.credentials.get('client_id'),
            'client_secret': self.credentials.get('client_secret'),
        }
        
        response = requests.post(self.token_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            self.credentials['access_token'] = token_data['access_token']
            return True
        
        return False
    
    def _oauth_flow(self) -> bool:
        """Full OAuth authentication flow"""
        # Implementation would involve user redirect to auth URL
        # and handling callback
        logger.warning("Full OAuth flow requires user interaction")
        return False
    
    def sync_candidates(self, limit: int = 100) -> Dict:
        """Sync candidates from Bullhorn"""
        try:
            params = {
                'count': limit,
                'fields': 'id,firstName,lastName,email,phone,skills,yearsOfExperience'
            }
            
            response = self.get('entity/Candidate', params=params)
            candidates = response.get('data', [])
            
            self.last_sync_time = datetime.now()
            
            return {
                'status': 'success',
                'candidates_synced': len(candidates),
                'data': candidates
            }
        
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def sync_jobs(self, limit: int = 100) -> Dict:
        """Sync jobs from Bullhorn"""
        try:
            params = {
                'count': limit,
                'fields': 'id,title,description,requiredSkills,minYearsOfExperience'
            }
            
            response = self.get('entity/JobOrder', params=params)
            jobs = response.get('data', [])
            
            self.last_sync_time = datetime.now()
            
            return {
                'status': 'success',
                'jobs_synced': len(jobs),
                'data': jobs
            }
        
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def push_candidate(self, candidate_data: Dict) -> Dict:
        """Push candidate to Bullhorn"""
        try:
            # Map internal fields to Bullhorn fields
            bullhorn_data = self.map_fields(candidate_data, reverse=True)
            
            response = self.post('entity/Candidate', bullhorn_data)
            
            return {
                'status': 'success',
                'bullhorn_id': response.get('id')
            }
        
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }


class GenericAPIConnector(APIConnector):
    """Generic connector for any REST API"""
    
    def authenticate(self) -> bool:
        """Authenticate using configured auth type"""
        try:
            if self.auth_type == 'test':
                # For testing purposes
                return True
            
            return self.test_connection()
        except Exception as e:
            logger.error(f"Generic API auth failed: {e}")
            return False
    
    def sync_data(self, resource: str, method: str = 'GET') -> Dict:
        """Generic data sync method"""
        try:
            if method.upper() == 'GET':
                data = self.get(resource)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.last_sync_time = datetime.now()
            
            return {
                'status': 'success',
                'data': data,
                'synced_at': self.last_sync_time.isoformat()
            }
        
        except Exception as e:
            return self.handle_error(e)


# Example usage
if __name__ == '__main__':
    # Example: Bullhorn integration
    bullhorn_config = {
        'provider': 'bullhorn',
        'base_url': 'https://rest.bullhornstaffing.com/rest-services/v1',
        'auth_type': 'oauth',
        'credentials': {
            'client_id': 'your_client_id',
            'client_secret': 'your_client_secret',
            'access_token': 'your_access_token',
        },
        'field_mappings': {
            'firstName': 'first_name',
            'lastName': 'last_name',
            'email': 'email',
            'phone': 'phone',
            'skills': 'skills',
        }
    }
    
    # Create connector
    bullhorn = BullhornConnector(bullhorn_config)
    
    # Test connection
    if bullhorn.test_connection():
        # Sync candidates
        result = bullhorn.sync_candidates()
        print(json.dumps(result, indent=2))
