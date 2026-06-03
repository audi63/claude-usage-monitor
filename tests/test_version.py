"""Garde-fou : la version doit être identique dans les deux sources.

`pyproject.toml` (`[project].version`, utilisé pour le paquet/PyPI/le tag) et
`claude_usage_monitor.__version__` (affiché dans l'app, comparé par l'updater)
sont bumpés à la main : ce test échoue s'ils divergent, ce qui évite de publier
un artefact qui s'affiche avec l'ancienne version (cf. incident 2.4.0 → 2.4.1).
"""

import tomllib
from pathlib import Path

from claude_usage_monitor import __version__

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def test_version_matches_pyproject():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    pyproject_version = data["project"]["version"]
    assert __version__ == pyproject_version, (
        f"Versions désynchronisées : __init__.py={__version__!r} != "
        f"pyproject.toml={pyproject_version!r}. Bumper les DEUX."
    )
