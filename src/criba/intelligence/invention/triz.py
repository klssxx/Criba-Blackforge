"""Data-oriented TRIZ principle registry (P09-T05 / T057).

Verifiable, immutable catalog of the 40 canonical TRIZ principles in stable
order, each result explicitly traceable to blueprint technique T057.

Honest scope (no unsupported claims):
- The 40 principle names are the widely published canonical list; the short
  descriptions are paraphrases written for this registry.
- NO 39x39 contradiction matrix is implemented, embedded or simulated here.
  A matrix requires a documented, licensed numeric dataset; without such a
  source this module exposes `CONTRADICTION_MATRIX_AVAILABLE = False` instead
  of fabricating one.
- A principle in this registry is a reasoning prompt only: listing it does NOT
  assert that any derived proposal is feasible, novel or patentable.
"""
from __future__ import annotations

from dataclasses import dataclass

TRIZ_TECHNIQUE_ID = "T057"

#: Explicitly False until a sourced, licensed contradiction-matrix dataset is
#: provided. Consumers must check this instead of assuming matrix support.
CONTRADICTION_MATRIX_AVAILABLE = False

PRINCIPLES_COUNT = 40


@dataclass(frozen=True)
class TrizPrinciple:
    """Immutable TRIZ principle entry, traceable to its blueprint technique."""

    number: int
    name: str
    description: str
    technique_id: str = TRIZ_TECHNIQUE_ID

    def __post_init__(self) -> None:
        if not 1 <= self.number <= PRINCIPLES_COUNT:
            raise ValueError(f"principle number out of range 1..{PRINCIPLES_COUNT}: {self.number}")
        if not self.name.strip():
            raise ValueError("principle name must not be empty")
        if not self.description.strip():
            raise ValueError("principle description must not be empty")
        if self.technique_id != TRIZ_TECHNIQUE_ID:
            raise ValueError(f"technique_id must be {TRIZ_TECHNIQUE_ID}")


_PRINCIPLES: tuple[TrizPrinciple, ...] = (
    TrizPrinciple(1, "Segmentation", "Divide an object or process into independent parts."),
    TrizPrinciple(2, "Taking out", "Separate the only necessary part or property from the whole."),
    TrizPrinciple(3, "Local quality", "Make each part perform best under its own local conditions."),
    TrizPrinciple(4, "Asymmetry", "Replace symmetrical shapes or actions with asymmetrical ones."),
    TrizPrinciple(5, "Merging", "Bring similar or contiguous objects together into one structure."),
    TrizPrinciple(6, "Universality", "Make one object perform several functions."),
    TrizPrinciple(7, "Nesting", "Place one object inside another, like a matryoshka doll."),
    TrizPrinciple(8, "Anti-weight", "Counteract an object's weight by merging it with lift or support."),
    TrizPrinciple(9, "Preliminary anti-action", "Introduce the opposite action beforehand to control a harmful one."),
    TrizPrinciple(10, "Preliminary action", "Prepare required changes in advance, fully or partially."),
    TrizPrinciple(11, "Beforehand cushion", "Prepare emergency means before an action becomes critical."),
    TrizPrinciple(12, "Equipotentiality", "Avoid raising or lowering objects by working in a constant-potential field."),
    TrizPrinciple(13, "Inversion", "Do the opposite: invert the action, make movable parts fixed."),
    TrizPrinciple(14, "Spheroidality", "Replace straight lines and flat surfaces with curves and spheres."),
    TrizPrinciple(15, "Dynamics", "Allow characteristics of an object to change for optimal performance."),
    TrizPrinciple(16, "Partial or excessive actions", "Slightly under- or over-do when exact results are hard."),
    TrizPrinciple(17, "Another dimension", "Move an object to a different dimension or layering."),
    TrizPrinciple(18, "Mechanical vibration", "Cause an object to oscillate or vary its frequency."),
    TrizPrinciple(19, "Periodic action", "Replace continuous action with periodic or impulse action."),
    TrizPrinciple(20, "Continuity of useful action", "Keep the useful action running without pauses."),
    TrizPrinciple(21, "Rushing", "Perform harmful or hazardous steps quickly."),
    TrizPrinciple(22, "Convert harm into benefit", "Use a harmful effect to achieve a useful one."),
    TrizPrinciple(23, "Feedback", "Introduce or invert feedback to control a process."),
    TrizPrinciple(24, "Intermediary", "Use an intermediate carrier or process between two objects."),
    TrizPrinciple(25, "Self-service", "Make an object serve itself by performing auxiliary functions."),
    TrizPrinciple(26, "Copying", "Replace an object with simple, available or optical copies."),
    TrizPrinciple(27, "Cheap short-living objects", "Replace an expensive object with many cheap disposable ones."),
    TrizPrinciple(28, "Mechanics substitution", "Replace mechanical means with sensory, electromagnetic or field means."),
    TrizPrinciple(29, "Pneumatics and hydraulics", "Use gas or liquid instead of solid parts."),
    TrizPrinciple(30, "Flexible shells and thin films", "Replace rigid structures with flexible shells or films."),
    TrizPrinciple(31, "Porous materials", "Make an object porous or add porous elements."),
    TrizPrinciple(32, "Color changes", "Change an object's color, transparency or emissivity."),
    TrizPrinciple(33, "Homogeneity", "Make interacting objects from the same material."),
    TrizPrinciple(34, "Discarding and recovering", "Discard used-up parts and restore them during work."),
    TrizPrinciple(35, "Parameter changes", "Change an object's physical state, density, flexibility or temperature."),
    TrizPrinciple(36, "Phase transitions", "Exploit the phenomena that occur during phase changes."),
    TrizPrinciple(37, "Thermal expansion", "Use expansion or contraction from heating or cooling."),
    TrizPrinciple(38, "Strong oxidants", "Replace normal air with enriched or ionized oxygen."),
    TrizPrinciple(39, "Inert atmosphere", "Replace the normal environment with an inert one."),
    TrizPrinciple(40, "Composite materials", "Change from uniform to composite materials."),
)


def list_principles() -> tuple[TrizPrinciple, ...]:
    """Return all 40 canonical principles in stable ascending-number order."""
    return _PRINCIPLES


def get_principle(number: int) -> TrizPrinciple:
    """Return the principle with the given number (1..40).

    Raises KeyError for any number outside the registry, so an invalid lookup
    fails loudly instead of silently returning a substitute.
    """
    if not 1 <= number <= PRINCIPLES_COUNT:
        raise KeyError(f"unknown TRIZ principle number: {number}")
    return _PRINCIPLES[number - 1]
