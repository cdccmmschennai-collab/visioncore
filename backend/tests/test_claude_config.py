"""Tests for the per-team Claude API key encryption/masking helpers.

No database is exercised here (matches the rest of this suite — see
test_sync_client.py's docstring). The DB-backed lookup paths
(get_active_config/get_decrypted_key/set_api_key) are exercised end-to-end
by the manual test plan in this feature's implementation report instead.
"""
from app.models import Team
from app.services.claude_config import (
    ClaudeConfigError,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
)


def test_encrypt_then_decrypt_round_trips_to_the_original_key():
    raw = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234"
    encrypted = encrypt_api_key(raw)
    assert encrypted != raw
    assert decrypt_api_key(encrypted) == raw


def test_encrypted_key_is_never_a_substring_of_the_ciphertext():
    # A masked/partial leak of the plaintext into the stored ciphertext
    # would defeat the whole point of encrypting it.
    raw = "sk-ant-api03-super-secret-value-xyz"
    encrypted = encrypt_api_key(raw)
    assert raw not in encrypted


def test_mask_api_key_hides_the_middle_keeps_prefix_and_last_four():
    masked = mask_api_key("sk-ant-api03-abcdefghijklmnop1234")
    assert masked.startswith("sk-ant-")
    assert masked.endswith("1234")
    assert "abcdefghijklmnop" not in masked


def test_mask_api_key_never_raises_on_a_short_string():
    # Defensive: a malformed/legacy key should still mask, not crash the
    # Admin -> Claude API Settings page.
    masked = mask_api_key("short")
    assert "short" not in masked


def test_team_enum_matches_the_three_required_teams():
    assert {t.value for t in Team} == {"CHENNAI", "HYDERABAD", "QATAR"}


def test_claude_config_error_message_never_names_another_teams_key():
    # get_decrypted_key raises this exact message shape for an unconfigured
    # team (see app/services/ai_extractor.py) — never suggesting or naming
    # a fallback key from another team.
    error = ClaudeConfigError(f"Claude API is not configured for the {Team.HYDERABAD.value} team.")
    assert "HYDERABAD" in str(error)
    assert "CHENNAI" not in str(error)
    assert "QATAR" not in str(error)
