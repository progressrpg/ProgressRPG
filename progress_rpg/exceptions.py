"""
Custom Exception Classes for Progress RPG

This module defines a hierarchy of custom exceptions for better error
categorization and handling throughout the application.
"""


class ProgressRPGError(Exception):
    """Base exception for all app errors"""
    pass


class QuestError(ProgressRPGError):
    """Quest-related errors"""
    pass


class ActivityError(ProgressRPGError):
    """Activity-related errors (for player/character activities)"""
    pass


class CharacterError(ProgressRPGError):
    """Character-related errors"""
    pass


class TimerError(ProgressRPGError):
    """Timer-related errors"""
    pass


class PlayerError(ProgressRPGError):
    """Player-related errors"""
    pass
