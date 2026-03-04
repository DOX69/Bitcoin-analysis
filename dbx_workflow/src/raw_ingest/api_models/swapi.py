from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class SwapiCharacter(BaseModel):
    name: str
    height: str
    mass: str
    hair_color: str
    skin_color: str
    eye_color: str
    birth_year: str
    gender: str
    homeworld: str
    films: List[str]
    species: List[str]
    vehicles: List[str]
    starships: List[str]
    created: str
    edited: str
    url: str


class SwapiResponse(BaseModel):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[SwapiCharacter]
