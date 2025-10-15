#!/usr/bin/env python3
"""
SSL Bypass Fix for Corporate Networks
This module provides SSL bypass functionality for APIs that fail due to corporate firewalls/proxies
"""

import ssl
import urllib3
import os
import sys
from typing import Optional

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLBypass:
    """SSL bypass utility for corporate network environments"""
    
    @staticmethod
    def enable_ssl_bypass():
        """Enable SSL bypass for all HTTP requests"""
        # Set environment variables to disable SSL verification
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        
        # Create unverified SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Monkey patch ssl module
        ssl._create_default_https_context = ssl._create_unverified_context
        
        print("✅ SSL bypass enabled for corporate network")
    
    @staticmethod
    def configure_praw_ssl_bypass():
        """Configure PRAW to bypass SSL verification"""
        import prawcore
        
        # Patch the requestor to use unverified SSL
        original_init = prawcore.requestor.Requestor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # Override the session to disable SSL verification
            if hasattr(self, '_http'):
                self._http.verify = False
        
        prawcore.requestor.Requestor.__init__ = patched_init
        print("✅ PRAW SSL bypass configured")
    
    @staticmethod
    def configure_requests_ssl_bypass():
        """Configure requests library to bypass SSL verification"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Create a custom adapter that disables SSL verification
        class SSLBypassAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                kwargs['ssl_context'] = ssl.create_default_context()
                kwargs['ssl_context'].check_hostname = False
                kwargs['ssl_context'].verify_mode = ssl.CERT_NONE
                return super().init_poolmanager(*args, **kwargs)
        
        # Patch requests.Session to use our adapter by default
        original_session_init = requests.Session.__init__
        
        def patched_session_init(self, *args, **kwargs):
            original_session_init(self, *args, **kwargs)
            self.mount('https://', SSLBypassAdapter())
            self.mount('http://', SSLBypassAdapter())
        
        requests.Session.__init__ = patched_session_init
        print("✅ Requests SSL bypass configured")
    
    @staticmethod
    def configure_slack_ssl_bypass():
        """Configure Slack SDK to bypass SSL verification"""
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            from slack_sdk import WebClient
            
            # Create SSL context for Slack clients
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Store the SSL context for use by Slack clients
            SSLBypass._slack_ssl_context = ssl_context
            print("✅ Slack SDK SSL bypass configured")
            
        except ImportError:
            print("⚠️  Slack SDK not available, skipping Slack SSL bypass")
    
    @staticmethod
    def get_slack_ssl_context():
        """Get the SSL context for Slack clients"""
        if hasattr(SSLBypass, '_slack_ssl_context'):
            return SSLBypass._slack_ssl_context
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context

def apply_ssl_bypass():
    """Apply all SSL bypass configurations"""
    SSLBypass.enable_ssl_bypass()
    
    try:
        SSLBypass.configure_praw_ssl_bypass()
    except ImportError:
        print("⚠️  PRAW not available, skipping PRAW SSL bypass")
    
    try:
        SSLBypass.configure_requests_ssl_bypass()
    except ImportError:
        print("⚠️  Requests not available, skipping requests SSL bypass")
    
    try:
        SSLBypass.configure_slack_ssl_bypass()
    except ImportError:
        print("⚠️  Slack SDK not available, skipping Slack SSL bypass")

if __name__ == "__main__":
    apply_ssl_bypass()

