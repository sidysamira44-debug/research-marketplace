"""
Custom DRF exception handler.
Returns consistent JSON error format across all API endpoints:
  { "success": false, "error": { "code": "...", "message": "...", "details": {...} } }
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "success": False,
            "error": {
                "code": _get_error_code(response.status_code),
                "message": _extract_message(response.data),
                "details": response.data if isinstance(response.data, dict) else {"non_field_errors": response.data},
            }
        }
        response.data = error_data
    else:
        # Unhandled exception → 500
        logger.exception(f"Unhandled exception in {context.get('view')}: {exc}")
        response = Response(
            {
                "success": False,
                "error": {
                    "code": "server_error",
                    "message": "خطای داخلی سرور. لطفاً دوباره تلاش کنید.",
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _get_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "too_many_requests",
        500: "server_error",
    }.get(status_code, "error")


def _extract_message(data) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        # Take the first field error
        for key, val in data.items():
            if isinstance(val, list) and val:
                return str(val[0])
            return str(val)
    if isinstance(data, list) and data:
        return str(data[0])
    return "خطایی رخ داده است"
