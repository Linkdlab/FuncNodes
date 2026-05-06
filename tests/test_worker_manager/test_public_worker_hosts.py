import sys

if sys.platform != "emscripten":
    from funcnodes.worker.worker_manager import (
        _connectable_worker_host,
        _public_worker_config,
        _public_worker_configs,
        _public_worker_host,
    )

    def test_public_worker_host_uses_request_host_for_bind_host():
        assert (
            _public_worker_host(
                configured_host="0.0.0.0",
                request_host="funcnodes.demoserver.xyz:9380",
            )
            == "funcnodes.demoserver.xyz"
        )

    def test_public_worker_host_keeps_explicit_public_host():
        assert (
            _public_worker_host(
                configured_host="worker.example.org",
                request_host="funcnodes.demoserver.xyz:9380",
            )
            == "worker.example.org"
        )

    def test_public_worker_config_rewrites_copy_only():
        worker_config = {
            "type": "WSWorker",
            "uuid": "demo",
            "host": "localhost",
            "port": 9382,
        }

        public_config = _public_worker_config(
            worker_config,
            request_host="funcnodes.demoserver.xyz:9380",
        )

        assert public_config["host"] == "funcnodes.demoserver.xyz"
        assert worker_config["host"] == "localhost"

    def test_public_worker_configs_rewrites_active_and_inactive_workers():
        workers = [
            {"uuid": "active", "host": "0.0.0.0", "port": 9382},
            {"uuid": "inactive", "host": "127.0.0.1", "port": 9383},
        ]

        public_workers = _public_worker_configs(
            workers,
            request_host="funcnodes.demoserver.xyz:9380",
        )

        assert [worker["host"] for worker in public_workers] == [
            "funcnodes.demoserver.xyz",
            "funcnodes.demoserver.xyz",
        ]
        assert [worker["host"] for worker in workers] == ["0.0.0.0", "127.0.0.1"]

    def test_connectable_worker_host_maps_bind_hosts_to_loopback():
        assert _connectable_worker_host("0.0.0.0") == "127.0.0.1"
        assert _connectable_worker_host("::") == "127.0.0.1"
        assert _connectable_worker_host("worker.example.org") == "worker.example.org"
