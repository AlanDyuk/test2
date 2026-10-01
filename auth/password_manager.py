"""Password authentication manager using native bcrypt with automatic password upgrade."""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

logger = logging.getLogger(__name__)


class PasswordManager:
    """Manages secure password hashing and verification using native bcrypt."""

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hash.
        Primary: native bcrypt.
        Legacy fallback: SHA-256 (for backwards compatibility).
        """
        if not hashed_password or not plain_password:
            return False

        p_bytes = plain_password.encode("utf-8")[:72]

        # 1. Primary verification: native bcrypt
        if (hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$")) and HAS_BCRYPT:
            try:
                h_bytes = hashed_password.encode("utf-8")
                return bcrypt.checkpw(p_bytes, h_bytes)
            except Exception as e:
                logger.error(f"Bcrypt verification error: {e}")
                return False

        # 2. Legacy SHA-256 check
        sha256_hash = hashlib.sha256(p_bytes).hexdigest()
        if sha256_hash == hashed_password:
            return True

        return False

    def hash_password(self, password: str) -> str:
        """Hash a plain password using salted native bcrypt (or SHA-256 fallback)."""
        p_bytes = password.encode("utf-8")
        if HAS_BCRYPT:
            # Truncate password to 72 bytes if needed (bcrypt limit)
            if len(p_bytes) > 72:
                p_bytes = p_bytes[:72]
            return bcrypt.hashpw(p_bytes, bcrypt.gensalt()).decode("utf-8")
        return hashlib.sha256(p_bytes).hexdigest()

    def check_password_file(self, filepath: str = ".env") -> Optional[str]:
        """
        Read APP_PASSWORD from .env file, hash it with bcrypt, and write back.
        """
        from pathlib import Path

        env_path = Path(filepath)
        if not env_path.exists():
            return None

        content = env_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.strip().startswith("APP_PASSWORD="):
                raw = line.split("=", 1)[1].strip()
                if not raw:
                    return None
                # If raw or plain SHA-256, upgrade to bcrypt
                if not raw.startswith("$2b$"):
                    hashed = self.hash_password(raw)
                    content = content.replace(line, f"APP_PASSWORD={hashed}")
                    env_path.write_text(content, encoding="utf-8")
                    return hashed
                return raw
        return None
