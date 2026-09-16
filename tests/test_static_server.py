import os
import subprocess
import httpx


def test_static_server_limits_requests_to_dashboard():
    server = subprocess.Popen(
        ["bash", "scripts/site-serve.sh"],
        env={**os.environ, "PORT": "0"},
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        url = server.stdout.readline().strip().removeprefix("Dashboard: ")
        with httpx.Client(base_url=url.removesuffix("/site/"), timeout=5) as client:
            for path in ["/site/", "/site/assets/js/api.js", "/site/pages/meters.html"]:
                assert client.get(path).status_code == 200
            for path in [
                "/.env",
                "/README.md",
                "/site/../.env",
                "/site/%2e%2e/.env",
                "/site/%2e%2e/README.md",
            ]:
                assert client.get(path).status_code == 404
    finally:
        server.terminate()
        server.wait(timeout=5)
