"""
module defining all errors for FuncNodes
"""


class FuncNodeError(Exception):
    """Base class for exceptions in this module."""


# region Node Errors


class NodeError(FuncNodeError):
    """Base class for Node errors"""


class NodeStructureError(NodeError):
    """Raised when a Node class is not properly structured"""


class NodeInitalizationError(NodeError):
    """Raised when a Node is not properly initialized"""


class NodeTypeError(NodeError):
    """Raised when a Node is not the correct type"""

class NotOperableException(NodeError):
    """Raised when a Node is not operable"""

class DisabledException(NodeError):
    """Raised when a Node is disabled"""

class TriggerException(NodeError):
    """Raised when an error occurs during a trigger"""

# endregion Node Errors

# region NodeIO Errors


class NodeIOError(Exception):
    """Base class for all IO errors."""


class MissingValueError(NodeIOError):
    """Raised when a required input is missing a value."""


class EdgeError(NodeIOError):
    """Base class for all edge errors."""


# endregion NodeIO Errors

# region NodeSpace Errors


class NodeSpaceError(FuncNodeError):
    """Base class for NodeSpace errors"""


class LibraryError(NodeSpaceError):
    """Raised when a NodeSpace library is not properly structured"""


class LibraryTypeError(LibraryError):
    """Raised when a NodeSpace library is not the correct type"""


# endregion NodeSpace Errors
