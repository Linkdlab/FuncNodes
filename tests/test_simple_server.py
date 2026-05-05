from funcnodes.runner._simple_server import _public_worker_manager_host


def test_public_worker_manager_host_uses_request_host_for_localhost():
    assert (
        _public_worker_manager_host(
            configured_host="localhost",
            request_host="funcnodes.demoserver.xyz:8001",
        )
        == "funcnodes.demoserver.xyz"
    )


def test_public_worker_manager_host_uses_request_host_for_container_bind_host():
    assert (
        _public_worker_manager_host(
            configured_host="0.0.0.0",
            request_host="funcnodes.demoserver.xyz:8001",
        )
        == "funcnodes.demoserver.xyz"
    )


def test_public_worker_manager_host_keeps_explicit_public_host():
    assert (
        _public_worker_manager_host(
            configured_host="workers.example.org",
            request_host="funcnodes.demoserver.xyz:8001",
        )
        == "workers.example.org"
    )


def test_public_worker_manager_host_handles_ipv6_request_host():
    assert (
        _public_worker_manager_host(
            configured_host="localhost",
            request_host="[2001:db8::1]:8001",
        )
        == "[2001:db8::1]"
    )
