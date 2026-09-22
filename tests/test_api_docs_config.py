from app.main import app, documentation_paths


def test_api_documentation_is_enabled_by_default() -> None:
    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/openapi.json"


def test_api_documentation_can_be_disabled_for_production() -> None:
    assert documentation_paths(False) == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }
