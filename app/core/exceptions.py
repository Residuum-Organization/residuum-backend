"""Exceções HTTP compartilhadas da aplicação."""

from typing import NoReturn

from fastapi import HTTPException, status


def _raise_http_exception(status_code: int, detail: str) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=detail)


def raise_bad_request(detail: str) -> NoReturn:
    _raise_http_exception(status.HTTP_400_BAD_REQUEST, detail)


def raise_unauthorized(detail: str) -> NoReturn:
    _raise_http_exception(status.HTTP_401_UNAUTHORIZED, detail)


def raise_forbidden(detail: str) -> NoReturn:
    _raise_http_exception(status.HTTP_403_FORBIDDEN, detail)


def raise_not_found(detail: str) -> NoReturn:
    _raise_http_exception(status.HTTP_404_NOT_FOUND, detail)


def raise_conflict(detail: str) -> NoReturn:
    _raise_http_exception(status.HTTP_409_CONFLICT, detail)
