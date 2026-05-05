"""myapp/utils.py — Shared utilities."""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("myapp")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        data = response.data
        if isinstance(data, list):
            response.data = {"detail": data[0] if data else "Error."}
        elif isinstance(data, dict) and "detail" not in data:
            first_key = next(iter(data))
            first_error = data[first_key]
            if isinstance(first_error, list):
                first_error = first_error[0]
            response.data = {"detail": str(first_error), "errors": data}
        return response
    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {"detail": "An unexpected server error occurred. Please try again later."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )