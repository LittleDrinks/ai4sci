import pytest

from server.world import World


@pytest.fixture
def world(tmp_path):
    return World(tmp_path / "world.db", tmp_path / "artifacts")


@pytest.fixture
def project(world, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("orbit research", encoding="utf-8")
    return world.create_project("orbits-49", root, "Why do planetary orbits remain stable?")
