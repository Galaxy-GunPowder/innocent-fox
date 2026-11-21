"""Innocent Fox: drive the browser from Python over a private pipe."""
from . import profile
from .browser import Browser, Frame, IfoxError, LoadError, Tab
from .profile import Profile, ProfileError

__all__ = ["Browser", "Tab", "Frame", "IfoxError", "LoadError", "profile", "Profile", "ProfileError"]
