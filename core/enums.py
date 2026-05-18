from enum import Enum


class PlaqueCategory(Enum):
    NONE = "NONE"
    MILD = "MILD"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTENSIVE = "EXTENSIVE"


class DecisionStability(Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class RiskLevel(Enum):
    LOW = "LOW"
    BORDERLINE = "BORDERLINE"
    INTERMEDIATE = "INTERMEDIATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
