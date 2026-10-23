from fastapi.testclient import TestClient
import main
import relay_vless
import shared


def test_login_rejects_malformed_json():
    client = TestClient(main.app)
    response = client.post(
        "/api/login",
        content='{"password":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid json"


def test_xray_ws_config_uses_inbound_sni_and_host():
    original_inbounds = main.INBOUNDS
    original_settings = main.SETTINGS
    main.INBOUNDS = {
        "test-inbound": {
            "name": "WS inbound",
            "protocol": "vless",
            "port": 443,
            "network": "ws",
            "security": "tls",
            "domain": "example.com",
            "sni": "cdn.example.com",
            "external_domain": "",
            "external_port": 443,
            "fingerprint": "chrome",
            "reality_settings": {},
            "xhttp_settings": {},
            "ws_settings": {"path": "/ws/test", "host": "custom.example.net"},
            "grpc_settings": {},
            "created_at": "2024-01-01T00:00:00",
        }
    }
    main.SETTINGS = {"domain": "example.com"}

    try:
        config = main.generate_xray_server_config("test-inbound")
    finally:
        main.INBOUNDS = original_inbounds
        main.SETTINGS = original_settings

    stream = config["inbounds"][0]["streamSettings"]
    assert stream["tlsSettings"]["serverName"] == "cdn.example.com"
    assert stream["wsSettings"]["headers"]["Host"] == "custom.example.net"


def test_shared_state_is_reused_across_modules():
    main.hourly_traffic.clear()
    shared.hourly_traffic.clear()

    main.hourly_traffic["12:00"] += 42

    assert main.hourly_traffic is shared.hourly_traffic
    assert main.hourly_traffic is relay_vless.hourly_traffic
    assert main.stats is shared.stats
    assert main.connections is shared.connections
    assert main.error_logs is shared.error_logs


def test_xray_ws_config_tolerates_missing_optional_settings():
    original_inbounds = main.INBOUNDS
    original_settings = main.SETTINGS
    main.INBOUNDS = {
        "test-inbound": {
            "name": "WS inbound",
            "protocol": "vless",
            "port": 443,
            "network": "ws",
            "security": "tls",
            "domain": "example.com",
            "sni": "",
            "external_domain": "",
            "external_port": 443,
            "fingerprint": "chrome",
            "reality_settings": None,
            "xhttp_settings": None,
            "ws_settings": None,
            "grpc_settings": None,
            "created_at": "2024-01-01T00:00:00",
        }
    }
    main.SETTINGS = {"domain": "example.com"}

    try:
        config = main.generate_xray_server_config("test-inbound")
    finally:
        main.INBOUNDS = original_inbounds
        main.SETTINGS = original_settings

    stream = config["inbounds"][0]["streamSettings"]
    assert stream["tlsSettings"]["serverName"] == "example.com"
    assert stream["wsSettings"]["headers"]["Host"] == "example.com"
