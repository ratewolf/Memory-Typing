"""Package smoke tests."""


def test_package_import() -> None:
    import memory_typing

    assert memory_typing.__version__ == "0.1.0"
