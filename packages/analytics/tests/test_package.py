from importlib.metadata import version

import ddq_analytics


def test_version_matches_installed_metadata() -> None:
    assert ddq_analytics.__version__ == version("ddq-analytics")


def test_package_is_typed() -> None:
    from importlib.resources import files

    assert files("ddq_analytics").joinpath("py.typed").is_file()
