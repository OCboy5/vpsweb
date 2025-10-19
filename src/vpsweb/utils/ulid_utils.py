"""
ULID Generation and Validation Utility for VPSWeb Repository System

This module provides ULID (Universally Unique Lexicographically Sortable Identifier)
generation and validation capabilities for the repository system.

Features:
- ULID generation with time-based sorting
- ULID validation and parsing
- Time extraction from ULIDs
- Monotonic ULID generation
- Custom encoding/decoding support
- Batch ULID generation
"""

import time
import random
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import struct


# ULID alphabet: Crockford's Base32
CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Encoding/decoding maps
ENCODE_MAP = {char: i for i, char in enumerate(CROCKFORD_BASE32)}
DECODE_MAP = {i: char for i, char in enumerate(CROCKFORD_BASE32)}


class ULIDError(Exception):
    """Base exception for ULID operations."""

    pass


class InvalidULIDError(ULIDError):
    """Invalid ULID format or encoding."""

    pass


class TimeOverflowError(ULIDError):
    """ULID time component overflow."""

    pass


@dataclass
class ULIDComponents:
    """Components of a parsed ULID."""

    timestamp: int  # Milliseconds since Unix epoch
    randomness: int  # Random component
    datetime: datetime  # Parsed datetime
    encoded: str  # Original encoded ULID


class ULIDGenerator:
    """
    Generates and validates ULIDs.

    ULIDs are 128-bit identifiers with:
    - 48-bit timestamp (milliseconds since Unix epoch)
    - 80-bit randomness for collision resistance
    - Lexicographically sortable
    - URL-safe encoding (Crockford's Base32)
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize ULID generator.

        Args:
            seed: Random seed for deterministic generation (testing only)
        """
        if seed is not None:
            random.seed(seed)
        self._last_time = 0
        self._last_random = 0

    def generate(self, timestamp_ms: Optional[int] = None) -> str:
        """
        Generate a new ULID.

        Args:
            timestamp_ms: Timestamp in milliseconds (uses current time if None)

        Returns:
            26-character ULID string
        """
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)

        # Handle time overflow (ULID supports up to 10889 AD)
        if timestamp_ms > 0xFFFFFFFFFFFF:
            raise TimeOverflowError(f"Timestamp too large: {timestamp_ms}")

        # Ensure monotonicity
        if timestamp_ms == self._last_time:
            randomness = self._last_random + 1
        else:
            randomness = self._generate_randomness()

        # Update tracking
        self._last_time = timestamp_ms
        self._last_random = randomness

        return self._encode_ulid(timestamp_ms, randomness)

    def generate_monotonic(self, timestamp_ms: Optional[int] = None) -> str:
        """
        Generate a monotonic ULID (guaranteed increasing).

        Args:
            timestamp_ms: Timestamp in milliseconds

        Returns:
            Monotonic ULID string
        """
        return self.generate(timestamp_ms)

    def generate_batch(self, count: int) -> List[str]:
        """
        Generate multiple ULIDs.

        Args:
            count: Number of ULIDs to generate

        Returns:
            List of ULID strings
        """
        if count <= 0:
            return []

        ulids = []
        for _ in range(count):
            ulids.append(self.generate())

        return ulids

    def parse(self, ulid: str) -> ULIDComponents:
        """
        Parse a ULID into its components.

        Args:
            ulid: ULID string to parse

        Returns:
            ULIDComponents object

        Raises:
            InvalidULIDError: If ULID is invalid
        """
        if not self.is_valid(ulid):
            raise InvalidULIDError(f"Invalid ULID format: {ulid}")

        try:
            # Decode the ULID
            timestamp, randomness = self._decode_ulid(ulid)

            # Convert timestamp to datetime
            dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

            return ULIDComponents(
                timestamp=timestamp, randomness=randomness, datetime=dt, encoded=ulid
            )

        except Exception as e:
            raise InvalidULIDError(f"Failed to parse ULID {ulid}: {str(e)}")

    def is_valid(self, ulid: str) -> bool:
        """
        Check if a ULID string is valid.

        Args:
            ulid: ULID string to validate

        Returns:
            True if valid
        """
        if not isinstance(ulid, str):
            return False

        # Check length
        if len(ulid) != 26:
            return False

        # Check characters
        if not re.match(r"^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$", ulid):
            return False

        return True

    def get_timestamp(self, ulid: str) -> int:
        """
        Extract timestamp from ULID.

        Args:
            ulid: ULID string

        Returns:
            Timestamp in milliseconds
        """
        if not self.is_valid(ulid):
            raise InvalidULIDError(f"Invalid ULID: {ulid}")

        # Decode only the timestamp part (first 48 bits)
        timestamp_part = ulid[:10]  # First 10 characters = 48 bits
        timestamp = 0

        for char in timestamp_part:
            timestamp = timestamp * 32 + ENCODE_MAP[char]

        return timestamp

    def get_datetime(self, ulid: str) -> datetime:
        """
        Extract datetime from ULID.

        Args:
            ulid: ULID string

        Returns:
            UTC datetime object
        """
        timestamp_ms = self.get_timestamp(ulid)
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

    def compare(self, ulid1: str, ulid2: str) -> int:
        """
        Compare two ULIDs lexicographically.

        Args:
            ulid1: First ULID
            ulid2: Second ULID

        Returns:
            -1 if ulid1 < ulid2, 0 if equal, 1 if ulid1 > ulid2
        """
        if not self.is_valid(ulid1) or not self.is_valid(ulid2):
            raise InvalidULIDError("Both ULIDs must be valid for comparison")

        if ulid1 < ulid2:
            return -1
        elif ulid1 > ulid2:
            return 1
        else:
            return 0

    def _generate_randomness(self) -> int:
        """Generate 80-bit random component."""
        # Generate 10 bytes (80 bits) of randomness
        randomness = 0
        for _ in range(10):
            randomness = randomness * 256 + random.randint(0, 255)
        return randomness

    def _encode_ulid(self, timestamp: int, randomness: int) -> str:
        """Encode timestamp and randomness into ULID string."""
        # Ensure values fit in their bit ranges
        timestamp &= 0xFFFFFFFFFFFF  # 48 bits
        randomness &= 0xFFFFFFFFFFFFFFFFFFFFFFFF  # 80 bits

        # Encode timestamp (48 bits = 8 base32 characters + 4 bits of the 9th)
        encoded = []
        value = (timestamp << 80) | randomness

        # Encode 128 bits as 26 base32 characters
        for _ in range(26):
            encoded.append(DECODE_MAP[value & 0x1F])
            value >>= 5

        # Reverse to get correct order
        return "".join(reversed(encoded))

    def _decode_ulid(self, ulid: str) -> tuple[int, int]:
        """Decode ULID string into timestamp and randomness."""
        value = 0

        for char in ulid:
            value = value * 32 + ENCODE_MAP[char]

        # Extract components
        randomness = value & 0xFFFFFFFFFFFFFFFFFFFFFFFF  # 80 bits
        timestamp = value >> 80  # 48 bits

        return timestamp, randomness

    def encode_binary(self, ulid: str) -> bytes:
        """
        Encode ULID to binary format.

        Args:
            ulid: ULID string

        Returns:
            16-byte binary representation
        """
        timestamp, randomness = self._decode_ulid(ulid)
        return struct.pack(">QQ", timestamp, randomness)

    def decode_binary(self, binary_data: bytes) -> str:
        """
        Decode binary data to ULID string.

        Args:
            binary_data: 16-byte binary data

        Returns:
            ULID string
        """
        if len(binary_data) != 16:
            raise InvalidULIDError("Binary data must be exactly 16 bytes")

        timestamp, randomness = struct.unpack(">QQ", binary_data)
        return self._encode_ulid(timestamp, randomness)


class ULIDPool:
    """
    Pool of pre-generated ULIDs for performance optimization.

    Useful when generating many ULIDs in quick succession.
    """

    def __init__(self, pool_size: int = 1000):
        """
        Initialize ULID pool.

        Args:
            pool_size: Number of ULIDs to pre-generate
        """
        self.pool_size = pool_size
        self._pool: List[str] = []
        self._generator = ULIDGenerator()
        self._refill()

    def _refill(self) -> None:
        """Refill the ULID pool."""
        self._pool = self._generator.generate_batch(self.pool_size)

    def get(self) -> str:
        """
        Get a ULID from the pool.

        Returns:
            ULID string
        """
        if not self._pool:
            self._refill()

        return self._pool.pop(0)

    def get_batch(self, count: int) -> List[str]:
        """
        Get multiple ULIDs from the pool.

        Args:
            count: Number of ULIDs needed

        Returns:
            List of ULID strings
        """
        if count <= 0:
            return []

        # If we don't have enough, generate more
        while len(self._pool) < count:
            self._pool.extend(self._generator.generate_batch(self.pool_size))

        result = self._pool[:count]
        self._pool = self._pool[count:]
        return result

    def size(self) -> int:
        """Get current pool size."""
        return len(self._pool)


# Global ULID generator instance
_ulid_generator: Optional[ULIDGenerator] = None
_ulid_pool: Optional[ULIDPool] = None


def get_ulid_generator() -> ULIDGenerator:
    """
    Get the global ULID generator instance.

    Returns:
        Global ULIDGenerator instance
    """
    global _ulid_generator
    if _ulid_generator is None:
        _ulid_generator = ULIDGenerator()
    return _ulid_generator


def get_ulid_pool() -> ULIDPool:
    """
    Get the global ULID pool instance.

    Returns:
        Global ULIDPool instance
    """
    global _ulid_pool
    if _ulid_pool is None:
        _ulid_pool = ULIDPool()
    return _ulid_pool


def generate_ulid(timestamp_ms: Optional[int] = None) -> str:
    """
    Generate a new ULID.

    Args:
        timestamp_ms: Timestamp in milliseconds (optional)

    Returns:
        26-character ULID string
    """
    generator = get_ulid_generator()
    return generator.generate(timestamp_ms)


def generate_ulid_batch(count: int) -> List[str]:
    """
    Generate multiple ULIDs.

    Args:
        count: Number of ULIDs to generate

    Returns:
        List of ULID strings
    """
    generator = get_ulid_generator()
    return generator.generate_batch(count)


def parse_ulid(ulid: str) -> ULIDComponents:
    """
    Parse a ULID into its components.

    Args:
        ulid: ULID string to parse

    Returns:
        ULIDComponents object
    """
    generator = get_ulid_generator()
    return generator.parse(ulid)


def is_valid_ulid(ulid: str) -> bool:
    """
    Check if a ULID string is valid.

    Args:
        ulid: ULID string to validate

    Returns:
        True if valid
    """
    generator = get_ulid_generator()
    return generator.is_valid(ulid)


def get_ulid_timestamp(ulid: str) -> int:
    """
    Extract timestamp from ULID.

    Args:
        ulid: ULID string

    Returns:
        Timestamp in milliseconds
    """
    generator = get_ulid_generator()
    return generator.get_timestamp(ulid)


def get_ulid_datetime(ulid: str) -> datetime:
    """
    Extract datetime from ULID.

    Args:
        ulid: ULID string

    Returns:
        UTC datetime object
    """
    generator = get_ulid_generator()
    return generator.get_datetime(ulid)


def compare_ulids(ulid1: str, ulid2: str) -> int:
    """
    Compare two ULIDs lexicographically.

    Args:
        ulid1: First ULID
        ulid2: Second ULID

    Returns:
        -1 if ulid1 < ulid2, 0 if equal, 1 if ulid1 > ulid2
    """
    generator = get_ulid_generator()
    return generator.compare(ulid1, ulid2)


def ulid_from_datetime(dt: datetime) -> str:
    """
    Generate ULID from datetime.

    Args:
        dt: DateTime object

    Returns:
        ULID string
    """
    timestamp_ms = int(dt.timestamp() * 1000)
    return generate_ulid(timestamp_ms)


def ulid_to_binary(ulid: str) -> bytes:
    """
    Convert ULID to binary format.

    Args:
        ulid: ULID string

    Returns:
        16-byte binary representation
    """
    generator = get_ulid_generator()
    return generator.encode_binary(ulid)


def binary_to_ulid(binary_data: bytes) -> str:
    """
    Convert binary data to ULID string.

    Args:
        binary_data: 16-byte binary data

    Returns:
        ULID string
    """
    generator = get_ulid_generator()
    return generator.decode_binary(binary_data)


def validate_ulid_list(ulids: List[str]) -> Dict[str, Any]:
    """
    Validate a list of ULIDs.

    Args:
        ulids: List of ULID strings to validate

    Returns:
        Dictionary with validation results
    """
    results = {
        "valid": [],
        "invalid": [],
        "duplicates": [],
        "count": len(ulids),
        "valid_count": 0,
        "invalid_count": 0,
        "duplicate_count": 0,
    }

    seen = set()

    for ulid in ulids:
        if is_valid_ulid(ulid):
            results["valid"].append(ulid)
            results["valid_count"] += 1

            if ulid in seen:
                results["duplicates"].append(ulid)
                results["duplicate_count"] += 1
            else:
                seen.add(ulid)
        else:
            results["invalid"].append(ulid)
            results["invalid_count"] += 1

    return results


def get_ulid_stats(ulids: List[str]) -> Dict[str, Any]:
    """
    Get statistics for a list of ULIDs.

    Args:
        ulids: List of ULID strings

    Returns:
        Dictionary with ULID statistics
    """
    if not ulids:
        return {
            "count": 0,
            "time_range": None,
            "oldest": None,
            "newest": None,
            "span_hours": 0,
        }

    timestamps = []
    valid_ulids = []

    for ulid in ulids:
        if is_valid_ulid(ulid):
            try:
                timestamp = get_ulid_timestamp(ulid)
                timestamps.append(timestamp)
                valid_ulids.append(ulid)
            except:
                continue

    if not timestamps:
        return {
            "count": len(ulids),
            "valid_count": 0,
            "time_range": None,
            "oldest": None,
            "newest": None,
            "span_hours": 0,
        }

    oldest_ts = min(timestamps)
    newest_ts = max(timestamps)
    span_hours = (newest_ts - oldest_ts) / (1000 * 60 * 60)

    return {
        "count": len(ulids),
        "valid_count": len(valid_ulids),
        "time_range": {
            "oldest_timestamp": oldest_ts,
            "newest_timestamp": newest_ts,
            "oldest_datetime": datetime.fromtimestamp(
                oldest_ts / 1000, tz=timezone.utc
            ).isoformat(),
            "newest_datetime": datetime.fromtimestamp(
                newest_ts / 1000, tz=timezone.utc
            ).isoformat(),
        },
        "oldest": valid_ulids[timestamps.index(oldest_ts)],
        "newest": valid_ulids[timestamps.index(newest_ts)],
        "span_hours": span_hours,
    }
