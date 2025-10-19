"""
Date/Time Utilities for VPSWeb Repository System

This module provides comprehensive date/time utilities with timezone support
for the repository system.

Features:
- Timezone-aware datetime handling
- ISO 8601 formatting and parsing
- Relative time calculations
- Time zone conversion utilities
- Duration formatting and parsing
- Workday and business time calculations
- Poetry-specific date formatting
"""

import re
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, Any, Union, Tuple
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta
import pytz
import calendar


class DateTimeError(Exception):
    """Base exception for datetime operations."""

    pass


class TimezoneError(DateTimeError):
    """Timezone-related errors."""

    pass


class ParsingError(DateTimeError):
    """Date/time parsing errors."""

    pass


class TimezoneManager:
    """
    Manages timezone operations and conversions.

    Provides utilities for working with different timezones
    and handling timezone-aware datetime objects.
    """

    # Common timezones for poetry translation
    COMMON_TIMEZONES = {
        "UTC": "UTC",
        "US/Eastern": "America/New_York",
        "US/Central": "America/Chicago",
        "US/Mountain": "America/Denver",
        "US/Pacific": "America/Los_Angeles",
        "Europe/London": "Europe/London",
        "Europe/Paris": "Europe/Paris",
        "Europe/Berlin": "Europe/Berlin",
        "Asia/Shanghai": "Asia/Shanghai",
        "Asia/Tokyo": "Asia/Tokyo",
        "Asia/Seoul": "Asia/Seoul",
        "Asia/Dubai": "Asia/Dubai",
        "Australia/Sydney": "Australia/Sydney",
    }

    def __init__(self, default_timezone: str = "UTC"):
        """
        Initialize timezone manager.

        Args:
            default_timezone: Default timezone to use
        """
        self.default_timezone = default_timezone
        self._timezone_cache: Dict[str, Any] = {}

    def get_timezone(self, tz_name: str) -> Any:
        """
        Get timezone object by name.

        Args:
            tz_name: Timezone name

        Returns:
            Timezone object

        Raises:
            TimezoneError: If timezone is invalid
        """
        if tz_name in self._timezone_cache:
            return self._timezone_cache[tz_name]

        try:
            # Try direct timezone lookup
            tz_obj = pytz.timezone(tz_name)
            self._timezone_cache[tz_name] = tz_obj
            return tz_obj
        except pytz.UnknownTimeZoneError:
            raise TimezoneError(f"Unknown timezone: {tz_name}")

    def convert_timezone(self, dt: datetime, from_tz: str, to_tz: str) -> datetime:
        """
        Convert datetime from one timezone to another.

        Args:
            dt: Datetime object
            from_tz: Source timezone
            to_tz: Target timezone

        Returns:
            Datetime in target timezone
        """
        from_timezone = self.get_timezone(from_tz)
        to_timezone = self.get_timezone(to_tz)

        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            dt = from_timezone.localize(dt)

        return dt.astimezone(to_timezone)

    def to_utc(self, dt: datetime, from_tz: Optional[str] = None) -> datetime:
        """
        Convert datetime to UTC.

        Args:
            dt: Datetime object
            from_tz: Source timezone (uses datetime's timezone if None)

        Returns:
            UTC datetime
        """
        if dt.tzinfo is None and from_tz:
            from_timezone = self.get_timezone(from_tz)
            dt = from_timezone.localize(dt)

        return dt.astimezone(timezone.utc)

    def from_utc(self, dt: datetime, to_tz: str) -> datetime:
        """
        Convert UTC datetime to target timezone.

        Args:
            dt: UTC datetime
            to_tz: Target timezone

        Returns:
            Datetime in target timezone
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        to_timezone = self.get_timezone(to_tz)
        return dt.astimezone(to_timezone)

    def now(self, tz_name: Optional[str] = None) -> datetime:
        """
        Get current time in specified timezone.

        Args:
            tz_name: Timezone name (uses default if None)

        Returns:
            Current datetime in specified timezone
        """
        tz_name = tz_name or self.default_timezone
        tz_obj = self.get_timezone(tz_name)
        return datetime.now(tz_obj)


class DateTimeFormatter:
    """
    Provides various datetime formatting options.

    Supports ISO 8601, human-readable, and poetry-specific formats.
    """

    # Standard formats
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    ISO_FORMAT_U = "%Y-%m-%dT%H:%M:%SZ"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Poetry-specific formats
    POETRY_DATE_FORMAT = "%B %d, %Y"  # "October 18, 2025"
    POETRY_DATETIME_FORMAT = "%B %d, %Y at %I:%M %p"  # "October 18, 2025 at 2:30 PM"
    CLASSICAL_FORMAT = "%d %B %Y"  # "18 October 2025"

    # Relative formats
    RELATIVE_FORMATS = {
        "seconds": "%S seconds",
        "minutes": "%M minutes",
        "hours": "%H hours",
        "days": "%d days",
        "weeks": "%W weeks",
        "months": "%M months",
        "years": "%Y years",
    }

    @staticmethod
    def to_iso_string(dt: datetime, microseconds: bool = False) -> str:
        """
        Convert datetime to ISO 8601 string.

        Args:
            dt: Datetime object
            microseconds: Whether to include microseconds

        Returns:
            ISO 8601 formatted string
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        if microseconds:
            return dt.isoformat()
        else:
            return dt.replace(microsecond=0).isoformat()

    @staticmethod
    def from_iso_string(iso_string: str) -> datetime:
        """
        Parse ISO 8601 string to datetime.

        Args:
            iso_string: ISO 8601 formatted string

        Returns:
            Datetime object

        Raises:
            ParsingError: If parsing fails
        """
        try:
            return parser.isoparse(iso_string)
        except Exception as e:
            raise ParsingError(f"Failed to parse ISO string '{iso_string}': {str(e)}")

    @staticmethod
    def to_poetry_date(dt: datetime) -> str:
        """
        Format datetime for poetry display.

        Args:
            dt: Datetime object

        Returns:
            Poetry-formatted date string
        """
        return dt.strftime(DateTimeFormatter.POETRY_DATE_FORMAT)

    @staticmethod
    def to_poetry_datetime(dt: datetime) -> str:
        """
        Format datetime for poetry display with time.

        Args:
            dt: Datetime object

        Returns:
            Poetry-formatted datetime string
        """
        return dt.strftime(DateTimeFormatter.POETRY_DATETIME_FORMAT)

    @staticmethod
    def format_duration(duration: timedelta) -> str:
        """
        Format duration in human-readable form.

        Args:
            duration: Duration to format

        Returns:
            Human-readable duration string
        """
        if duration.total_seconds() < 60:
            return f"{int(duration.total_seconds())} seconds"
        elif duration.total_seconds() < 3600:
            return f"{int(duration.total_seconds() / 60)} minutes"
        elif duration.total_seconds() < 86400:
            return f"{int(duration.total_seconds() / 3600)} hours"
        else:
            return f"{int(duration.total_seconds() / 86400)} days"

    @staticmethod
    def parse_duration(duration_str: str) -> timedelta:
        """
        Parse duration string to timedelta.

        Args:
            duration_str: Duration string (e.g., "2 hours", "30 minutes")

        Returns:
            Timedelta object

        Raises:
            ParsingError: If parsing fails
        """
        try:
            return parser.parse(duration_str)
        except Exception as e:
            raise ParsingError(f"Failed to parse duration '{duration_str}': {str(e)}")


class TimeCalculator:
    """
    Provides time calculation utilities.

    Handles relative time, business days, and poetry-specific calculations.
    """

    @staticmethod
    def time_ago(dt: datetime, reference: Optional[datetime] = None) -> str:
        """
        Calculate time ago from datetime.

        Args:
            dt: Datetime to calculate from
            reference: Reference datetime (uses now if None)

        Returns:
            Human-readable time ago string
        """
        if reference is None:
            reference = datetime.now(timezone.utc)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        delta = reference - dt
        absolute_delta = abs(delta)

        if absolute_delta.total_seconds() < 60:
            seconds = int(absolute_delta.total_seconds())
            return f"{seconds} second{'s' if seconds != 1 else ''} {'ago' if delta.total_seconds() > 0 else 'from now'}"
        elif absolute_delta.total_seconds() < 3600:
            minutes = int(absolute_delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} {'ago' if delta.total_seconds() > 0 else 'from now'}"
        elif absolute_delta.total_seconds() < 86400:
            hours = int(absolute_delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} {'ago' if delta.total_seconds() > 0 else 'from now'}"
        elif absolute_delta.days < 30:
            days = absolute_delta.days
            return f"{days} day{'s' if days != 1 else ''} {'ago' if delta.total_seconds() > 0 else 'from now'}"
        elif absolute_delta.days < 365:
            months = int(absolute_delta.days / 30)
            return f"{months} month{'s' if months != 1 else ''} {'ago' if delta.total_seconds() > 0 else 'from now'}"
        else:
            years = int(absolute_delta.days / 365)
            return f"{years} year{'s' if years != 1 else ''} {'ago' if delta.total_seconds() > 0 else 'from now'}"

    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        """
        Check if datetime falls on a weekend.

        Args:
            dt: Datetime to check

        Returns:
            True if it's a weekend
        """
        return dt.weekday() >= 5  # Saturday=5, Sunday=6

    @staticmethod
    def is_business_hours(
        dt: datetime, start_hour: int = 9, end_hour: int = 17
    ) -> bool:
        """
        Check if datetime falls within business hours.

        Args:
            dt: Datetime to check
            start_hour: Business start hour (24-hour format)
            end_hour: Business end hour (24-hour format)

        Returns:
            True if within business hours
        """
        return start_hour <= dt.hour < end_hour and not TimeCalculator.is_weekend(dt)

    @staticmethod
    def add_business_days(dt: datetime, days: int) -> datetime:
        """
        Add business days to datetime.

        Args:
            dt: Starting datetime
            days: Number of business days to add

        Returns:
            Datetime after adding business days
        """
        result = dt
        added_days = 0

        while added_days < days:
            result += timedelta(days=1)
            if not TimeCalculator.is_weekend(result):
                added_days += 1

        return result

    @staticmethod
    def get_age(
        birth_date: Union[date, datetime], reference: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Calculate age from birth date.

        Args:
            birth_date: Birth date or datetime
            reference: Reference datetime (uses now if None)

        Returns:
            Dictionary with years, months, days
        """
        if reference is None:
            reference = datetime.now(timezone.utc)

        # Convert date to datetime if needed
        if isinstance(birth_date, date) and not isinstance(birth_date, datetime):
            birth_date = datetime.combine(birth_date, datetime.min.time())
            if reference.tzinfo:
                birth_date = birth_date.replace(tzinfo=reference.tzinfo)

        if birth_date.tzinfo is None and reference.tzinfo:
            birth_date = birth_date.replace(tzinfo=reference.tzinfo)
        elif birth_date.tzinfo is not None and reference.tzinfo is None:
            reference = reference.replace(tzinfo=birth_date.tzinfo)

        delta = relativedelta(reference, birth_date)

        return {"years": delta.years, "months": delta.months, "days": delta.days}

    @staticmethod
    def get_season(dt: datetime, hemisphere: str = "northern") -> str:
        """
        Get season for datetime.

        Args:
            dt: Datetime to check
            hemisphere: 'northern' or 'southern'

        Returns:
            Season name
        """
        month = dt.month

        if hemisphere.lower() == "northern":
            if month in [12, 1, 2]:
                return "Winter"
            elif month in [3, 4, 5]:
                return "Spring"
            elif month in [6, 7, 8]:
                return "Summer"
            else:
                return "Autumn"
        else:
            if month in [12, 1, 2]:
                return "Summer"
            elif month in [3, 4, 5]:
                return "Autumn"
            elif month in [6, 7, 8]:
                return "Winter"
            else:
                return "Spring"

    @staticmethod
    def get_quarter(dt: datetime) -> int:
        """
        Get quarter for datetime.

        Args:
            dt: Datetime to check

        Returns:
            Quarter number (1-4)
        """
        return (dt.month - 1) // 3 + 1

    @staticmethod
    def get_week_number(dt: datetime) -> int:
        """
        Get ISO week number for datetime.

        Args:
            dt: Datetime to check

        Returns:
            ISO week number
        """
        return dt.isocalendar()[1]

    @staticmethod
    def get_day_of_year(dt: datetime) -> int:
        """
        Get day of year for datetime.

        Args:
            dt: Datetime to check

        Returns:
            Day of year (1-366)
        """
        return dt.timetuple().tm_yday


class PoetryDateTimeUtils:
    """
    Poetry-specific datetime utilities.

    Provides formatting and calculations specific to poetry and translation work.
    """

    @staticmethod
    def format_creation_date(dt: datetime, style: str = "modern") -> str:
        """
        Format creation date for poetry display.

        Args:
            dt: Creation datetime
            style: 'modern', 'classical', 'academic'

        Returns:
            Formatted date string
        """
        if style == "modern":
            return DateTimeFormatter.to_poetry_date(dt)
        elif style == "classical":
            return dt.strftime(DateTimeFormatter.CLASSICAL_FORMAT)
        elif style == "academic":
            return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        else:
            return DateTimeFormatter.to_poetry_date(dt)

    @staticmethod
    def format_translation_date(dt: datetime, include_time: bool = True) -> str:
        """
        Format translation date for display.

        Args:
            dt: Translation datetime
            include_time: Whether to include time

        Returns:
            Formatted date string
        """
        if include_time:
            return DateTimeFormatter.to_poetry_datetime(dt)
        else:
            return DateTimeFormatter.to_poetry_date(dt)

    @staticmethod
    def calculate_translation_speed(
        word_count: int, start_time: datetime, end_time: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Calculate translation speed metrics.

        Args:
            word_count: Number of words translated
            start_time: Translation start time
            end_time: Translation end time (uses now if None)

        Returns:
            Dictionary with speed metrics
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        duration_seconds = (end_time - start_time).total_seconds()
        duration_hours = duration_seconds / 3600

        if duration_hours > 0:
            words_per_hour = word_count / duration_hours
        else:
            words_per_hour = 0

        if duration_seconds > 0:
            words_per_minute = word_count / (duration_seconds / 60)
        else:
            words_per_minute = 0

        return {
            "word_count": word_count,
            "duration_seconds": duration_seconds,
            "duration_hours": duration_hours,
            "words_per_hour": words_per_hour,
            "words_per_minute": words_per_minute,
        }

    @staticmethod
    def get_poetry_period(dt: datetime) -> str:
        """
        Get historical poetry period for a date.

        Args:
            dt: Datetime to classify

        Returns:
            Poetry period name
        """
        year = dt.year

        if year < 500:
            return "Classical Antiquity"
        elif year < 1000:
            return "Early Medieval"
        elif year < 1300:
            return "High Medieval"
        elif year < 1500:
            return "Late Medieval"
        elif year < 1600:
            return "Renaissance"
        elif year < 1700:
            return "Baroque"
        elif year < 1800:
            return "Enlightenment"
        elif year < 1850:
            return "Romantic"
        elif year < 1900:
            return "Victorian"
        elif year < 1950:
            return "Modernist"
        elif year < 2000:
            return "Contemporary"
        else:
            return "21st Century"


# Global instances
_timezone_manager: Optional[TimezoneManager] = None


def get_timezone_manager() -> TimezoneManager:
    """
    Get the global timezone manager instance.

    Returns:
        Global TimezoneManager instance
    """
    global _timezone_manager
    if _timezone_manager is None:
        _timezone_manager = TimezoneManager()
    return _timezone_manager


# Convenience functions
def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc(dt: datetime, from_tz: Optional[str] = None) -> datetime:
    """Convert datetime to UTC."""
    manager = get_timezone_manager()
    return manager.to_utc(dt, from_tz)


def from_utc(dt: datetime, to_tz: str) -> datetime:
    """Convert UTC datetime to target timezone."""
    manager = get_timezone_manager()
    return manager.from_utc(dt, to_tz)


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime string."""
    return DateTimeFormatter.from_iso_string(iso_string)


def format_iso_datetime(dt: datetime, microseconds: bool = False) -> str:
    """Format datetime as ISO 8601 string."""
    return DateTimeFormatter.to_iso_string(dt, microseconds)


def time_ago(dt: datetime, reference: Optional[datetime] = None) -> str:
    """Calculate time ago from datetime."""
    return TimeCalculator.time_ago(dt, reference)


def format_poetry_date(dt: datetime, style: str = "modern") -> str:
    """Format date for poetry display."""
    return PoetryDateTimeUtils.format_creation_date(dt, style)


def get_age(
    birth_date: Union[date, datetime], reference: Optional[datetime] = None
) -> Dict[str, int]:
    """Calculate age from birth date."""
    return TimeCalculator.get_age(birth_date, reference)


def is_valid_datetime_string(date_string: str) -> bool:
    """Check if string can be parsed as datetime."""
    try:
        parser.parse(date_string)
        return True
    except:
        return False


def parse_flexible_datetime(date_string: str) -> datetime:
    """
    Parse datetime from flexible string formats.

    Args:
        date_string: Date string in various formats

    Returns:
        Parsed datetime object

    Raises:
        ParsingError: If parsing fails
    """
    try:
        dt = parser.parse(date_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception as e:
        raise ParsingError(f"Failed to parse datetime '{date_string}': {str(e)}")
