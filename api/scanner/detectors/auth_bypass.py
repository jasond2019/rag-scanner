"""
Auth Bypass Detector (Simplified)
Detects if API can be accessed without proper authentication
"""

import re
from typing import Dict, List
from .base import BaseDetector


class AuthBypassDetector(BaseDetector):
    """认证绕过检测器"""

    SEVERITY = "high"
    SCORE_DEDUCTION = 10
    RULE_ID = "RAG-SEC-005"

    def detect(self, target_url: str, headers: Dict, task_id: str) -> List[Dict]:
        """执行认证绕过检测"""
        vulnerabilities = []

        # Test 1: Request without auth header
        test_headers = {"Content-Type": "application/json"}
        status, response = self.send_request(
            target_url,
            "Hello, this is a test",
            test_headers
        )

        # If we get a successful response without auth, it's a vulnerability
        if status and status in [200, 201]:
            # Check if response contains actual data (not just an error message)
            if response and len(response) > 50:
                if "error" not in response.lower() and "unauthorized" not in response.lower():
                    vulnerabilities.append(
                        self.create_vulnerability(
                            name="Authentication Bypass",
                            description="API responds to requests without authentication",
                            suggestion="Enforce authentication on all API endpoints",
                            evidence=["Request without auth header returned successful response"],
                        )
                    )

        # Test 2: Check if API has rate limiting (send multiple requests)
        # Simplified: just check if there's rate limiting by response headers

        return vulnerabilities