from criba.llm_adapter import CloudBackend


class _Response:
    status_code = 200


class _Client:
    def __init__(self) -> None:
        self.requested_url = ""

    def get(self, url: str) -> _Response:
        self.requested_url = url
        return _Response()


def test_cloud_availability_uses_configured_base_url() -> None:
    backend = CloudBackend("test-token", base_url="https://example.test/v1/")
    client = _Client()
    backend.client = client  # type: ignore[assignment]

    assert backend.is_available()
    assert client.requested_url == "https://example.test/v1/models"
