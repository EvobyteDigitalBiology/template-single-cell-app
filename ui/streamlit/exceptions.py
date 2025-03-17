# tCodeApp/exceptions.py

"""
Module containing custom exceptions for UI.
"""

class UIAppError(Exception):
    """Base class for UI exceptions."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
