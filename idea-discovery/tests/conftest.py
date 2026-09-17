import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from idea_discovery.families import get_family  # noqa: E402


@pytest.fixture(scope="session")
def domino():
    return get_family("domino_tiling")


@pytest.fixture(scope="session")
def population():
    return get_family("population_game")


@pytest.fixture(scope="session")
def domino_impossible(domino):
    return domino.generate_instance(8, 1, answer="impossible")


@pytest.fixture(scope="session")
def domino_possible(domino):
    return domino.generate_instance(8, 2, answer="possible")


@pytest.fixture(scope="session")
def population_impossible(population):
    return population.generate_instance(24, 1, answer="impossible")


@pytest.fixture(scope="session")
def population_possible(population):
    return population.generate_instance(24, 2, answer="possible")


@pytest.fixture
def all_conditions():
    return {"free_solve": True, "posthoc": True, "supplied_idea": True, "recognition": True}
