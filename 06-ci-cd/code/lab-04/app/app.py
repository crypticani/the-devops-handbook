"""The thing being built. Deliberately tiny — the lab is about the pipeline."""


def release_name(version: str, environment: str) -> str:
    """Build the release tag a deployment would use."""
    if not version:
        raise ValueError("version is required")
    return f"{environment}-{version}"


def demo() -> None:
    assert release_name("1.4.2", "prod") == "prod-1.4.2"
    assert release_name("0.1.0", "dev") == "dev-0.1.0"
    try:
        release_name("", "dev")
    except ValueError:
        pass
    else:
        raise AssertionError("empty version should raise")
    print("app self-check: ok")


if __name__ == "__main__":
    demo()
