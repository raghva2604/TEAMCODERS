import time

from ai.afferens import generate_ai_observation, should_send_alert
from alerts.telegram import get_telegram_settings, validate_telegram_credentials


def test_should_send_alert_for_new_person():
    last_alert_time = {}
    now = time.time()

    should_send, next_time = should_send_alert("Unknown", last_alert_time, 30, now)

    assert should_send is True
    assert next_time == now
    assert last_alert_time["Unknown"] == now


def test_should_block_alert_during_cooldown():
    last_alert_time = {"Unknown": time.time()}
    now = last_alert_time["Unknown"] + 10

    should_send, _ = should_send_alert("Unknown", last_alert_time, 30, now)

    assert should_send is False


def test_generate_ai_observation_contains_expected_keys():
    report = generate_ai_observation(people=1, objects=["Laptop", "Backpack"], environment="Indoor", lighting="Normal", risk="LOW")

    assert report["people"] == 1
    assert report["objects"] == ["Laptop", "Backpack"]
    assert report["environment"] == "Indoor"
    assert report["lighting"] == "Normal"
    assert report["risk"] == "LOW"
    assert "summary" in report


def test_validate_telegram_credentials_rejects_malformed_values():
    valid, error = validate_telegram_credentials("invalid-token", "6387624723")

    assert valid is False
    assert "invalid" in error.lower()


def test_get_telegram_settings_reloads_dotenv_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqRstUVWxyz1234567890123\nTELEGRAM_CHAT_ID=123456789\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "stale-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")

    token, chat_id = get_telegram_settings(str(env_file))

    assert token == "123456789:ABCdefGHIjklMNOpqRstUVWxyz1234567890123"
    assert chat_id == "123456789"
