"""
Content Negotiation and Response Formatting for VPSWeb Repository System.

This module provides comprehensive content negotiation support, allowing
the API to serve responses in multiple formats (JSON, XML, CSV, etc.)
with proper media type handling and content negotiation.

Features:
- Multi-format response support (JSON, XML, CSV, HTML)
- Content negotiation based on Accept headers
- Automatic response format detection
- Media type registration and handling
- Response formatting utilities
- Error handling for unsupported formats
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from enum import Enum
import csv
import io
import json
from xml.etree import ElementTree as ET
from xml.dom import minidom

from fastapi import Request, Response
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    HTMLResponse,
    StreamingResponse,
    ORJSONResponse
)
from pydantic import BaseModel

T = TypeVar('T')


class ResponseFormat(str, Enum):
    """Supported response formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    HTML = "html"
    TEXT = "text"
    ORJSON = "orjson"


class MediaTypes:
    """Standard media type mappings."""
    APPLICATION_JSON = "application/json"
    APPLICATION_XML = "application/xml"
    TEXT_XML = "text/xml"
    TEXT_CSV = "text/csv"
    TEXT_HTML = "text/html"
    TEXT_PLAIN = "text/plain"
    APPLICATION_ORJSON = "application/json"  # orjson uses same media type


# Media type mapping
FORMAT_MEDIA_TYPES: Dict[ResponseFormat, str] = {
    ResponseFormat.JSON: MediaTypes.APPLICATION_JSON,
    ResponseFormat.XML: MediaTypes.APPLICATION_XML,
    ResponseFormat.CSV: MediaTypes.TEXT_CSV,
    ResponseFormat.HTML: MediaTypes.TEXT_HTML,
    ResponseFormat.TEXT: MediaTypes.TEXT_PLAIN,
    ResponseFormat.ORJSON: MediaTypes.APPLICATION_ORJSON,
}

# Media type to format mapping (reverse lookup)
MEDIA_TYPE_FORMATS: Dict[str, ResponseFormat] = {
    v: k for k, v in FORMAT_MEDIA_TYPES.items()
}


class ContentNegotiator:
    """
    Handles content negotiation for API responses.

    Supports parsing Accept headers and determining the best
    response format based on client preferences and server capabilities.
    """

    def __init__(self, default_format: ResponseFormat = ResponseFormat.JSON):
        """
        Initialize content negotiator.

        Args:
            default_format: Default response format when no preference specified
        """
        self.default_format = default_format
        self.supported_formats = list(FORMAT_MEDIA_TYPES.keys())

    def negotiate_content(
        self,
        accept_header: Optional[str] = None,
        format_param: Optional[str] = None
    ) -> ResponseFormat:
        """
        Negotiate content based on Accept header and format parameter.

        Args:
            accept_header: HTTP Accept header value
            format_param: Format query parameter (takes precedence)

        Returns:
            Negotiated response format
        """
        # Format query parameter takes precedence over Accept header
        if format_param:
            try:
                format_param_format = ResponseFormat(format_param.lower())
                if format_param_format in self.supported_formats:
                    return format_param_format
            except ValueError:
                pass  # Invalid format, continue with Accept header

        # Parse Accept header if provided
        if accept_header:
            return self._parse_accept_header(accept_header)

        # Fall back to default format
        return self.default_format

    def _parse_accept_header(self, accept_header: str) -> ResponseFormat:
        """
        Parse Accept header and determine best format.

        Args:
            accept_header: Accept header string

        Returns:
            Best matching response format
        """
        if not accept_header:
            return self.default_format

        # Parse Accept header: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        media_ranges = accept_header.split(',')

        # Create list of (media_type, quality_factor) tuples
        candidates = []
        for media_range in media_ranges:
            media_range = media_range.strip()
            if not media_range:
                continue

            # Split media type and parameters
            parts = media_range.split(';')
            media_type = parts[0].strip().lower()

            # Extract quality factor
            quality = 1.0
            for part in parts[1:]:
                part = part.strip()
                if part.startswith('q='):
                    try:
                        quality = float(part[2:])
                    except ValueError:
                        quality = 0.0
                    break

            candidates.append((media_type, quality))

        # Sort by quality factor (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Find first matching supported format
        for media_type, quality in candidates:
            if quality <= 0:
                continue

            # Exact match
            if media_type in MEDIA_TYPE_FORMATS:
                return MEDIA_TYPE_FORMATS[media_type]

            # Wildcard match
            if media_type == '*/*' or media_type == 'application/*':
                # Return default format for wildcard matches
                return self.default_format

            # Partial match (e.g., "application/*" matches "application/json")
            if '*' in media_type:
                base_type = media_type.split('/')[0] + '/*'
                for format_type, format_media in FORMAT_MEDIA_TYPES.items():
                    if format_media.startswith(base_type):
                        return format_type

        # No match found, return default
        return self.default_format

    def get_media_type(self, format: ResponseFormat) -> str:
        """
        Get media type for format.

        Args:
            format: Response format

        Returns:
            Media type string
        """
        return FORMAT_MEDIA_TYPES.get(format, MediaTypes.APPLICATION_JSON)

    def is_format_supported(self, format: Union[str, ResponseFormat]) -> bool:
        """
        Check if format is supported.

        Args:
            format: Format to check

        Returns:
            True if supported, False otherwise
        """
        if isinstance(format, str):
            try:
                format = ResponseFormat(format.lower())
            except ValueError:
                return False

        return format in self.supported_formats


class ResponseFormatter:
    """
    Formats responses in different formats.

    Provides conversion utilities for transforming data into
    various response formats with proper serialization.
    """

    @staticmethod
    def format_json(data: Any, use_orjson: bool = False) -> str:
        """
        Format data as JSON.

        Args:
            data: Data to format
            use_orjson: Whether to use orjson for faster serialization

        Returns:
            JSON string
        """
        if use_orjson:
            try:
                import orjson
                return orjson.dumps(data).decode()
            except ImportError:
                pass

        return json.dumps(data, default=str, ensure_ascii=False)

    @staticmethod
    def format_xml(data: Any, root_element: str = "root") -> str:
        """
        Format data as XML.

        Args:
            data: Data to format (should be dict or list)
            root_element: Root element name

        Returns:
            XML string
        """
        def dict_to_xml(tag: str, d: Any) -> ET.Element:
            """Convert dictionary to XML element."""
            elem = ET.Element(tag)

            if isinstance(d, dict):
                for key, value in d.items():
                    # Handle invalid XML characters in key names
                    clean_key = str(key).replace(' ', '_').replace('-', '_')
                    if clean_key.isalnum() or '_' in clean_key:
                        child = dict_to_xml(clean_key, value)
                        elem.append(child)
                    else:
                        # Use generic item element for invalid keys
                        child = dict_to_xml("item", value)
                        child.set("key", str(key))
                        elem.append(child)
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    child = dict_to_xml(f"{tag[:-1]}", item) if tag.endswith('s') else dict_to_xml("item", item)
                    elem.append(child)
            else:
                elem.text = str(d)

            return elem

        if isinstance(data, list):
            root = ET.Element(root_element)
            for item in data:
                if isinstance(item, dict):
                    child = dict_to_xml("item", item)
                else:
                    child = ET.Element("item")
                    child.text = str(item)
                root.append(child)
        elif isinstance(data, dict):
            root = dict_to_xml(root_element, data)
        else:
            root = ET.Element(root_element)
            root.text = str(data)

        # Pretty print XML
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    @staticmethod
    def format_csv(data: List[Dict[str, Any]]) -> str:
        """
        Format data as CSV.

        Args:
            data: List of dictionaries to format

        Returns:
            CSV string
        """
        if not data:
            return ""

        output = io.StringIO()

        # Get all unique keys from all rows
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())

        fieldnames = sorted(all_keys)

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for row in data:
            # Convert all values to strings
            csv_row = {k: str(v) if v is not None else "" for k, v in row.items()}
            writer.writerow(csv_row)

        return output.getvalue()

    @staticmethod
    def format_html(data: Any, title: str = "Data") -> str:
        """
        Format data as basic HTML table.

        Args:
            data: Data to format
            title: HTML page title

        Returns:
            HTML string
        """
        def value_to_html(value: Any) -> str:
            """Convert value to HTML-safe string."""
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, default=str)
            return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        html_parts = [
            f"<!DOCTYPE html>",
            f"<html>",
            f"<head>",
            f"    <title>{title}</title>",
            f"    <meta charset='utf-8'>",
            f"    <style>",
            f"        body {{ font-family: Arial, sans-serif; margin: 20px; }}",
            f"        table {{ border-collapse: collapse; width: 100%; }}",
            f"        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}",
            f"        th {{ background-color: #f2f2f2; }}",
            f"        .json {{ white-space: pre-wrap; font-family: monospace; }}",
            f"    </style>",
            f"</head>",
            f"<body>",
            f"    <h1>{title}</h1>"
        ]

        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Table format for list of dictionaries
            all_keys = set()
            for row in data:
                all_keys.update(row.keys())

            fieldnames = sorted(all_keys)

            html_parts.append("    <table>")
            html_parts.append("        <tr>")
            for field in fieldnames:
                html_parts.append(f"            <th>{field}</th>")
            html_parts.append("        </tr>")

            for row in data:
                html_parts.append("        <tr>")
                for field in fieldnames:
                    value = row.get(field, "")
                    html_parts.append(f"            <td>{value_to_html(value)}</td>")
                html_parts.append("        </tr>")

            html_parts.append("    </table>")
        else:
            # JSON format for other data types
            html_parts.append("    <div class='json'>")
            html_parts.append(value_to_html(data))
            html_parts.append("    </div>")

        html_parts.extend([
            f"</body>",
            f"</html>"
        ])

        return "\n".join(html_parts)


class NegotiatedResponse:
    """
    Creates responses with content negotiation support.

    Automatically handles content negotiation and formats responses
    based on client preferences.
    """

    def __init__(self, negotiator: Optional[ContentNegotiator] = None):
        """
        Initialize negotiated response handler.

        Args:
            negotiator: Content negotiator instance
        """
        self.negotiator = negotiator or ContentNegotiator()
        self.formatter = ResponseFormatter()

    def create_response(
        self,
        data: Any,
        request: Request,
        format_param: Optional[str] = None,
        root_element: str = "data",
        title: str = "API Response"
    ) -> Response:
        """
        Create a response with content negotiation.

        Args:
            data: Data to include in response
            request: FastAPI request object
            format_param: Optional format parameter
            root_element: Root element name for XML
            title: Title for HTML responses

        Returns:
            Formatted response
        """
        # Negotiate content format
        accept_header = request.headers.get("accept")
        format = self.negotiator.negotiate_content(accept_header, format_param)

        # Get media type
        media_type = self.negotiator.get_media_type(format)

        # Format data based on format
        if format == ResponseFormat.JSON:
            content = self.formatter.format_json(data)
            return Response(content, media_type=media_type)

        elif format == ResponseFormat.ORJSON:
            content = self.formatter.format_json(data, use_orjson=True)
            return ORJSONResponse(content)

        elif format == ResponseFormat.XML:
            content = self.formatter.format_xml(data, root_element)
            return Response(content, media_type=media_type)

        elif format == ResponseFormat.CSV:
            if not isinstance(data, list):
                # Convert to list for CSV
                if isinstance(data, dict):
                    data = [data]
                else:
                    data = [{"value": data}]
            content = self.formatter.format_csv(data)
            return Response(content, media_type=media_type)

        elif format == ResponseFormat.HTML:
            content = self.formatter.format_html(data, title)
            return HTMLResponse(content)

        elif format == ResponseFormat.TEXT:
            content = self.formatter.format_json(data)  # Use JSON as text format
            return PlainTextResponse(content)

        else:
            # Unsupported format, return error
            error_data = {
                "error": True,
                "message": f"Unsupported response format: {format}",
                "supported_formats": self.negotiator.supported_formats
            }
            content = self.formatter.format_json(error_data)
            return Response(
                content,
                status_code=406,
                media_type=MediaTypes.APPLICATION_JSON
            )

    def create_error_response(
        self,
        error_data: Dict[str, Any],
        request: Request,
        status_code: int = 400
    ) -> Response:
        """
        Create an error response with content negotiation.

        Args:
            error_data: Error data to include
            request: FastAPI request object
            status_code: HTTP status code

        Returns:
            Formatted error response
        """
        return self.create_response(error_data, request, title="API Error")


# Global content negotiator instance
default_negotiator = ContentNegotiator()
default_response_handler = NegotiatedResponse(default_negotiator)


def negotiate_response(
    data: Any,
    request: Request,
    format_param: Optional[str] = None,
    root_element: str = "data",
    title: str = "API Response"
) -> Response:
    """
    Convenience function for creating negotiated responses.

    Args:
        data: Data to include in response
        request: FastAPI request object
        format_param: Optional format parameter
        root_element: Root element name for XML
        title: Title for HTML responses

    Returns:
        Formatted response
    """
    return default_response_handler.create_response(
        data, request, format_param, root_element, title
    )


def negotiate_error_response(
    error_data: Dict[str, Any],
    request: Request,
    status_code: int = 400
) -> Response:
    """
    Convenience function for creating negotiated error responses.

    Args:
        error_data: Error data to include
        request: FastAPI request object
        status_code: HTTP status code

    Returns:
        Formatted error response
    """
    return default_response_handler.create_error_response(
        error_data, request, status_code
    )