def test_package_exposes_a_version() -> None:
    from agents_tools import __version__

    assert __version__
