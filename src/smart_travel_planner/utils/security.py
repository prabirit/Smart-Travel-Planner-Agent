"""Security utilities for Smart Travel Planner."""

import re
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..exceptions import ValidationError


def sanitize_input(input_string: str, max_length: int = 255) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not isinstance(input_string, str):
        raise ValidationError("Input must be a string")
    
    # Remove potentially dangerous characters
    dangerous_chars = r'[<>"\'&;()]'
    sanitized = re.sub(dangerous_chars, '', input_string.strip())
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
    """Hash sensitive data using SHA-256 with salt."""
    if not isinstance(data, str):
        raise ValidationError("Data to hash must be a string")
    
    # Generate salt if not provided
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine data with salt
    salted_data = f"{salt}{data}"
    
    # Hash using SHA-256
    hashed = hashlib.sha256(salted_data.encode()).hexdigest()
    
    return f"{salt}${hashed}"


def verify_hash(data: str, hashed_data: str) -> bool:
    """Verify data against a hash."""
    if not isinstance(data, str) or not isinstance(hashed_data, str):
        return False
    
    try:
        salt, hash_value = hashed_data.split('$', 1)
        expected_hash = hash_sensitive_data(data, salt)
        return secrets.compare_digest(expected_hash, hashed_data)
    except ValueError:
        return False


def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(length)


def mask_sensitive_info(text: str, mask_char: str = '*') -> str:
    """Mask sensitive information in text for logging."""
    if not isinstance(text, str):
        return text
    
    # Common patterns to mask
    patterns = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', lambda m: mask_email(m.group())),
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', lambda m: mask_credit_card(m.group())),
        (r'\b\d{3}-\d{2}-\d{4}\b', lambda m: mask_ssn(m.group())),
        (r'\b[A-Za-z]{2}\d{6,}\b', lambda m: mask_passport(m.group())),
    ]
    
    masked_text = text
    for pattern, mask_func in patterns:
        masked_text = re.sub(pattern, mask_func, masked_text)
    
    return masked_text


def mask_email(email: str) -> str:
    """Mask email address for logging."""
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_credit_card(card_number: str) -> str:
    """Mask credit card number."""
    # Remove non-digit characters
    digits = re.sub(r'\D', '', card_number)
    
    if len(digits) < 4:
        return '*' * len(card_number)
    
    # Show last 4 digits
    return '*' * (len(digits) - 4) + digits[-4:]


def mask_ssn(ssn: str) -> str:
    """Mask Social Security Number."""
    return '***-**-' + ssn[-4:]


def mask_passport(passport: str) -> str:
    """Mask passport number."""
    if len(passport) <= 3:
        return '*' * len(passport)
    return passport[0] + '*' * (len(passport) - 3) + passport[-2:]


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength and return feedback."""
    if not isinstance(password, str):
        raise ValidationError("Password must be a string")
    
    feedback = {
        'is_strong': False,
        'score': 0,
        'issues': [],
        'suggestions': []
    }
    
    # Length check
    if len(password) < 8:
        feedback['issues'].append('Password must be at least 8 characters long')
        feedback['suggestions'].append('Use a longer password')
    else:
        feedback['score'] += 1
    
    # Uppercase check
    if not re.search(r'[A-Z]', password):
        feedback['issues'].append('Password must contain uppercase letters')
        feedback['suggestions'].append('Include uppercase letters')
    else:
        feedback['score'] += 1
    
    # Lowercase check
    if not re.search(r'[a-z]', password):
        feedback['issues'].append('Password must contain lowercase letters')
        feedback['suggestions'].append('Include lowercase letters')
    else:
        feedback['score'] += 1
    
    # Number check
    if not re.search(r'\d', password):
        feedback['issues'].append('Password must contain numbers')
        feedback['suggestions'].append('Include numbers')
    else:
        feedback['score'] += 1
    
    # Special character check
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        feedback['issues'].append('Password must contain special characters')
        feedback['suggestions'].append('Include special characters')
    else:
        feedback['score'] += 1
    
    # Common patterns check
    common_patterns = [
        r'123456',
        r'password',
        r'qwerty',
        r'admin',
        r'letmein'
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password, re.IGNORECASE):
            feedback['issues'].append('Password contains common patterns')
            feedback['suggestions'].append('Avoid common patterns')
            feedback['score'] -= 1
            break
    
    # Determine strength
    feedback['is_strong'] = feedback['score'] >= 4 and len(feedback['issues']) == 0
    
    return feedback


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def is_safe_url(url: str, allowed_hosts: Optional[list] = None) -> bool:
    """Check if URL is safe for redirects."""
    if not isinstance(url, str):
        return False
    
    # Basic URL validation
    url_patterns = [
        r'^https?://',  # Must start with http:// or https://
        r'^/',          # Or be a relative URL
    ]
    
    if not any(re.match(pattern, url) for pattern in url_patterns):
        return False
    
    # Check against allowed hosts if provided
    if allowed_hosts and not url.startswith('/'):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.netloc not in allowed_hosts:
                return False
        except Exception:
            return False
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'<script',
        r'onclick',
        r'onload',
    ]
    
    if any(re.search(pattern, url, re.IGNORECASE) for pattern in dangerous_patterns):
        return False
    
    return True


def rate_limit_key(identifier: str, window_minutes: int = 60) -> str:
    """Generate a rate limit key for the current time window."""
    now = datetime.utcnow()
    window_start = now.replace(
        minute=(now.minute // window_minutes) * window_minutes,
        second=0,
        microsecond=0
    )
    
    key_data = f"{identifier}:{window_start.isoformat()}"
    return hashlib.md5(key_data.encode()).hexdigest()


def encrypt_sensitive_field(value: str, encryption_key: str) -> str:
    """Simple field encryption (for demonstration - use proper encryption in production)."""
    # This is a simple XOR cipher for demonstration
    # In production, use proper encryption like AES
    if not isinstance(value, str) or not isinstance(encryption_key, str):
        raise ValidationError("Both value and encryption key must be strings")
    
    key_bytes = encryption_key.encode()
    value_bytes = value.encode()
    
    encrypted = bytearray()
    for i, byte in enumerate(value_bytes):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    
    return encrypted.hex()


def decrypt_sensitive_field(encrypted_value: str, encryption_key: str) -> str:
    """Decrypt a field encrypted with encrypt_sensitive_field."""
    if not isinstance(encrypted_value, str) or not isinstance(encryption_key, str):
        raise ValidationError("Both encrypted value and encryption key must be strings")
    
    try:
        key_bytes = encryption_key.encode()
        encrypted_bytes = bytes.fromhex(encrypted_value)
        
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return decrypted.decode()
    except ValueError:
        raise ValidationError("Invalid encrypted value format")
