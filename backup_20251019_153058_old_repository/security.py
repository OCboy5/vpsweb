"""
Security Middleware for VPSWeb Repository System

This module provides security middleware for HTTP security headers,
XSS protection, and other security-related HTTP middleware.

Features:
- HTTP security headers middleware
- XSS protection headers
- Content Security Policy (CSP)
- CORS configuration
- Rate limiting middleware
- Request logging and monitoring
"""

import time
import hashlib
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime, timezone
from urllib.parse import urlparse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.exceptions import HTTPException
from fastapi import status

from ..utils.logger import get_structured_logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding HTTP security headers to responses.

    Implements OWASP recommended security headers for web applications.
    """

    def __init__(
        self,
        app,
        include_subdomains: bool = True,
        report_uri: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application instance
            include_subdomains: Whether to include subdomains in security policies
            report_uri: URI for reporting security violations
            custom_headers: Additional custom security headers
        """
        super().__init__(app)
        self.include_subdomains = include_subdomains
        self.report_uri = report_uri
        self.custom_headers = custom_headers or {}
        self.logger = get_structured_logger()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Add security headers to the response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # Enforces HTTPS connections
        max_age = 31536000  # 1 year
        if self.include_subdomains:
            response.headers["Strict-Transport-Security"] = f"max-age={max_age}; includeSubDomains; preload"
        else:
            response.headers["Strict-Transport-Security"] = f"max-age={max_age}"

        # X-Content-Type-Options
        # Prevents MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevents clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection
        # Enables XSS protection in browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # Controls referrer information sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy (CSP)
        # Defines approved content sources
        csp_directives = self._build_csp_directives(request)
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions-Policy
        # Controls browser features and APIs
        permissions_policy = self._build_permissions_policy()
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # Custom security headers
        for header_name, header_value in self.custom_headers.items():
            response.headers[header_name] = header_value

        # Log security headers (debug level to avoid spam)
        self.logger.debug(
            "Security headers added to response",
            path=request.url.path,
            method=request.method,
            security_headers=list(response.headers.keys())
        )

        return response

    def _build_csp_directives(self, request: Request) -> List[str]:
        """
        Build Content Security Policy directives.

        Args:
            request: Current request for context

        Returns:
            List of CSP directive strings
        """
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        # Add report-uri if provided
        if self.report_uri:
            directives.append(f"report-uri {self.report_uri}")
            directives.append("report-to csp-endpoint")

        return directives

    def _build_permissions_policy(self) -> List[str]:
        """
        Build Permissions Policy directives.

        Returns:
            List of Permissions Policy strings
        """
        policies = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
            "fullscreen=(self)",
            "clipboard-read=(self)",
            "clipboard-write=(self)",
        ]

        return policies


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Additional XSS protection middleware.

    Provides deeper XSS protection beyond basic headers.
    """

    def __init__(self, app, enable_content_check: bool = False):
        """
        Initialize XSS protection middleware.

        Args:
            app: FastAPI application instance
            enable_content_check: Whether to scan response content
        """
        super().__init__(app)
        self.enable_content_check = enable_content_check
        self.logger = get_structured_logger()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Apply XSS protection to responses.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response with XSS protection applied
        """
        response = await call_next(request)

        # Add additional XSS protection headers
        response.headers["X-Content-Security-Policy"] = "default-src 'self'"

        # Log potential XSS attempts
        user_agent = request.headers.get("User-Agent", "")
        suspicious_patterns = ["<script", "javascript:", "onerror=", "onload="]

        for pattern in suspicious_patterns:
            if pattern.lower() in user_agent.lower():
                self.logger.warning(
                    "Suspicious User-Agent detected",
                    user_agent=user_agent,
                    pattern=pattern,
                    client_ip=request.client.host if request.client else "unknown"
                )
                break

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.

    Provides basic rate limiting based on client IP.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        exempt_paths: Optional[Set[str]] = None
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance
            requests_per_minute: Maximum requests per minute per IP
            burst_size: Maximum burst size
            exempt_paths: Set of paths to exempt from rate limiting
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.exempt_paths = exempt_paths or {"/health", "/metrics", "/docs", "/openapi.json"}
        self.clients: Dict[str, Dict] = {}
        self.logger = get_structured_logger()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Apply rate limiting to requests.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response or rate limit error
        """
        # Check if path is exempt
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean up old entries
        self._cleanup_old_entries(current_time)

        # Get or create client entry
        client_data = self.clients.get(client_ip, {
            "requests": [],
            "count": 0,
            "last_reset": current_time
        })

        # Check if we need to reset the counter (1 minute window)
        if current_time - client_data["last_reset"] > 60:
            client_data["requests"] = []
            client_data["count"] = 0
            client_data["last_reset"] = current_time

        # Check rate limit
        if client_data["count"] >= self.requests_per_minute:
            self.logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                requests_count=client_data["count"],
                limit=self.requests_per_minute
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )

        # Record this request
        client_data["requests"].append(current_time)
        client_data["count"] += 1
        self.clients[client_ip] = client_data

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_old_entries(self, current_time: float) -> None:
        """
        Clean up old client entries.

        Args:
            current_time: Current timestamp
        """
        cutoff_time = current_time - 300  # 5 minutes
        clients_to_remove = []

        for client_ip, client_data in self.clients.items():
            if client_data["last_reset"] < cutoff_time:
                clients_to_remove.append(client_ip)

        for client_ip in clients_to_remove:
            del self.clients[client_ip]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware for security monitoring.

    Logs all HTTP requests with security-relevant information.
    """

    def __init__(self, app, log_body: bool = False, max_body_size: int = 1000):
        """
        Initialize request logging middleware.

        Args:
            app: FastAPI application instance
            log_body: Whether to log request/response bodies
            max_body_size: Maximum body size to log
        """
        super().__init__(app)
        self.log_body = log_body
        self.max_body_size = max_body_size
        self.logger = get_structured_logger()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Log request and response information.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response after logging
        """
        start_time = time.time()

        # Gather request information
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
            "content_type": request.headers.get("Content-Type", ""),
            "content_length": request.headers.get("Content-Length", "0")
        }

        # Log suspicious patterns
        self._check_suspicious_patterns(request, request_info)

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)

        # Gather response information
        response_info = {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "content_length": response.headers.get("Content-Length", "0"),
            "process_time": process_time
        }

        # Log the request/response
        log_level = "warning" if response.status_code >= 400 else "info"
        getattr(self.logger, log_level)(
            "HTTP request processed",
            **request_info,
            **response_info
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host

        return "unknown"

    def _check_suspicious_patterns(self, request: Request, request_info: Dict) -> None:
        """
        Check for suspicious patterns in the request.

        Args:
            request: HTTP request
            request_info: Dictionary to populate with suspicious info
        """
        suspicious_patterns = {
            "sql_injection": ["union select", "drop table", "insert into", "delete from"],
            "xss": ["<script", "javascript:", "onerror=", "onload=", "vbscript:"],
            "path_traversal": ["../", "..\\", "%2e%2e%2f"],
            "command_injection": ["; rm", "| cat", "&&", "||", "`"]
        }

        query_string = str(request.query_params).lower()
        user_agent = request_info["user_agent"].lower()

        for attack_type, patterns in suspicious_patterns.items():
            for pattern in patterns:
                if pattern in query_string or pattern in user_agent:
                    self.logger.warning(
                        f"Suspicious pattern detected: {attack_type}",
                        pattern=pattern,
                        **request_info
                    )
                    break


def setup_security_middleware(
    app,
    enable_cors: bool = True,
    enable_compression: bool = True,
    enable_rate_limiting: bool = True,
    enable_request_logging: bool = True,
    custom_config: Optional[Dict] = None
) -> None:
    """
    Set up all security middleware for a FastAPI application.

    Args:
        app: FastAPI application instance
        enable_cors: Whether to enable CORS middleware
        enable_compression: Whether to enable GZIP compression
        enable_rate_limiting: Whether to enable rate limiting
        enable_request_logging: Whether to enable request logging
        custom_config: Custom configuration overrides
    """
    config = custom_config or {}
    logger = get_structured_logger()

    # Add security headers middleware (always first)
    app.add_middleware(
        SecurityHeadersMiddleware,
        include_subdomains=config.get("hsts_include_subdomains", True),
        report_uri=config.get("csp_report_uri"),
        custom_headers=config.get("custom_headers", {})
    )

    # Add XSS protection middleware
    app.add_middleware(
        XSSProtectionMiddleware,
        enable_content_check=config.get("xss_content_check", False)
    )

    # Add CORS middleware if enabled
    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get("cors_origins", ["http://localhost:3000", "http://localhost:8080"]),
            allow_credentials=config.get("cors_credentials", True),
            allow_methods=config.get("cors_methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
            allow_headers=config.get("cors_headers", ["*"]),
        )

    # Add compression middleware if enabled
    if enable_compression:
        app.add_middleware(
            GZipMiddleware,
            minimum_size=config.get("compression_min_size", 1000)
        )

    # Add rate limiting middleware if enabled
    if enable_rate_limiting:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=config.get("rate_limit_per_minute", 60),
            burst_size=config.get("rate_limit_burst", 10),
            exempt_paths=set(config.get("rate_limit_exempt_paths", ["/health", "/metrics", "/docs", "/openapi.json"]))
        )

    # Add request logging middleware if enabled (always last to capture everything)
    if enable_request_logging:
        app.add_middleware(
            RequestLoggingMiddleware,
            log_body=config.get("log_request_body", False),
            max_body_size=config.get("log_max_body_size", 1000)
        )

    logger.info(
        "Security middleware configured",
        cors_enabled=enable_cors,
        compression_enabled=enable_compression,
        rate_limiting_enabled=enable_rate_limiting,
        request_logging_enabled=enable_request_logging
    )


# Enhanced CORS Configuration Classes
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SecurityLevel(str, Enum):
    """Security levels for different deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class CORSConfig:
    """
    Enhanced CORS configuration for web UI access.

    Provides comprehensive CORS configuration with origins whitelist,
    method restrictions, and security considerations.
    """

    # Origins configuration
    allowed_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ])
    blocked_origins: List[str] = field(default_factory=list)
    allowed_origin_regex: List[str] = field(default_factory=list)

    # Methods and headers
    allowed_methods: List[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"
    ])
    allowed_headers: List[str] = field(default_factory=lambda: [
        "Accept", "Accept-Language", "Content-Language", "Content-Type",
        "Authorization", "X-Requested-With", "X-CSRF-Token"
    ])
    exposed_headers: List[str] = field(default_factory=lambda: [
        "X-Total-Count", "X-Page-Count", "X-Per-Page"
    ])

    # Credentials and caching
    allow_credentials: bool = True
    max_age: int = 86400  # 24 hours
    preflight_continue: bool = True
    preflight_max_age: int = 86400

    # Security settings
    enforce_origin: bool = True
    validate_origin_header: bool = True

    @classmethod
    def for_development(cls) -> 'CORSConfig':
        """Create development-friendly CORS configuration."""
        return cls(
            allowed_origins=[
                "http://localhost:3000",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3001",  # Additional dev ports
                "http://127.0.0.1:3001",
            ],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_credentials=True,
            enforce_origin=False,  # More lenient in development
        )

    @classmethod
    def for_production(cls) -> 'CORSConfig':
        """Create production-grade CORS configuration."""
        return cls(
            allowed_origins=[
                # Add your production frontend domains here
                # "https://yourdomain.com",
                # "https://app.yourdomain.com",
                # "https://www.yourdomain.com",
            ],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],  # More restrictive
            allow_credentials=True,
            max_age=7200,  # 2 hours
            enforce_origin=True,
            validate_origin_header=True,
        )

    @classmethod
    def for_staging(cls) -> 'CORSConfig':
        """Create staging environment CORS configuration."""
        return cls(
            allowed_origins=[
                "https://staging.yourdomain.com",
                "https://preview.yourdomain.com",
                "http://localhost:3000",  # Allow local testing
            ],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_credentials=True,
            max_age=3600,  # 1 hour
            enforce_origin=True,
        )


def setup_cors_for_web_ui(
    app,
    security_level: SecurityLevel = SecurityLevel.DEVELOPMENT,
    custom_origins: Optional[List[str]] = None,
    custom_config: Optional[Dict] = None
) -> None:
    """
    Set up CORS configuration specifically for web UI access.

    Args:
        app: FastAPI application instance
        security_level: Security level (development, staging, production)
        custom_origins: Additional allowed origins
        custom_config: Additional CORS configuration overrides
    """
    logger = get_structured_logger()

    # Get base configuration for security level
    if security_level == SecurityLevel.DEVELOPMENT:
        cors_config = CORSConfig.for_development()
    elif security_level == SecurityLevel.PRODUCTION:
        cors_config = CORSConfig.for_production()
    elif security_level == SecurityLevel.STAGING:
        cors_config = CORSConfig.for_staging()
    else:
        cors_config = CORSConfig()  # Default

    # Apply custom origins if provided
    if custom_origins:
        cors_config.allowed_origins.extend(custom_origins)

    # Apply custom config overrides
    if custom_config:
        for key, value in custom_config.items():
            if hasattr(cors_config, key):
                setattr(cors_config, key, value)

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.allowed_origins,
        allow_origin_regex="|".join(cors_config.allowed_origin_regex) if cors_config.allowed_origin_regex else None,
        allow_methods=cors_config.allowed_methods,
        allow_headers=cors_config.allowed_headers,
        expose_headers=cors_config.exposed_headers,
        allow_credentials=cors_config.allow_credentials,
        max_age=cors_config.max_age,
    )

    logger.info(
        "CORS configured for web UI",
        security_level=security_level.value,
        allowed_origins_count=len(cors_config.allowed_origins),
        allow_credentials=cors_config.allow_credentials,
        max_age=cors_config.max_age
    )


def get_cors_status(app) -> Dict[str, Any]:
    """
    Get current CORS configuration status.

    Args:
        app: FastAPI application instance

    Returns:
        CORS configuration status
    """
    # This is a simplified version - in practice, you'd need to
    # inspect the middleware stack to get actual configuration
    return {
        "cors_enabled": True,
        "security_level": "development",  # This would be tracked elsewhere
        "allowed_origins_count": 0,  # Would need middleware inspection
        "allow_credentials": True,
        "max_age": 86400,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }