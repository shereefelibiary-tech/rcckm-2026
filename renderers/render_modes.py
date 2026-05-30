from enum import Enum


class RenderMode(str, Enum):
    """Audience-specific rendering mode for clinical vs patient-facing text."""

    CLINICIAN = "clinician"
    PATIENT = "patient"
