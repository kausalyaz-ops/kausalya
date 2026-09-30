"""Domain exceptions raised by the analysis pipeline."""


class InvalidDatasetError(Exception):
    """Raised when required source fields or critical values are invalid."""