"""Tests for the PII Anonymizer."""

from api.services.anonymizer import anonymize, anonymize_batch


class TestAnonymizeEmail:
    def test_simple_email(self):
        r = anonymize("Contact john@gmail.com for help")
        assert "[EMAIL]" in r.text
        assert "john@gmail.com" not in r.text
        assert r.redaction_count == 1

    def test_multiple_emails(self):
        r = anonymize("Email alice@test.com or bob@company.org")
        assert r.text.count("[EMAIL]") == 2
        assert r.redaction_count == 2

    def test_no_email(self):
        r = anonymize("No email here")
        assert r.text == "No email here"
        assert r.redaction_count == 0


class TestAnonymizeIP:
    def test_ipv4(self):
        r = anonymize("Server at 192.168.1.100 is down")
        assert "[IP]" in r.text
        assert "192.168.1.100" not in r.text

    def test_public_ip(self):
        r = anonymize("Connect to 54.231.0.15:8080")
        assert "[IP]" in r.text


class TestAnonymizePhone:
    def test_international(self):
        r = anonymize("Call +1 (555) 123-4567")
        assert "[PHONE]" in r.text
        assert "555" not in r.text

    def test_simple(self):
        r = anonymize("My number: (415) 555-0199")
        assert "[PHONE]" in r.text


class TestAnonymizeFilePath:
    def test_macos_path(self):
        r = anonymize("Error in /Users/johndoe/projects/app.py")
        assert "[PATH]" in r.text
        assert "johndoe" not in r.text

    def test_linux_path(self):
        r = anonymize("Check /home/admin/.ssh/config")
        assert "[PATH]" in r.text
        assert "admin" not in r.text


class TestAnonymizeAPIKey:
    def test_openai_key(self):
        r = anonymize("key: sk-abcdefghijklmnopqrstuvwxyz1234567890")
        assert "[API_KEY]" in r.text
        assert "sk-" not in r.text

    def test_github_pat(self):
        r = anonymize("token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh")
        assert "[API_KEY]" in r.text

    def test_aws_key(self):
        r = anonymize("AKIAIOSFODNN7EXAMPLE")
        assert "[API_KEY]" in r.text


class TestAnonymizeDiscordMention:
    def test_simple_mention(self):
        r = anonymize("Hey @johndoe check this out")
        assert "[USER]" in r.text
        assert "johndoe" not in r.text

    def test_mention_with_discriminator(self):
        r = anonymize("Ask @alice#1234 about it")
        assert "[USER]" in r.text


class TestAnonymizeURLAuth:
    def test_url_with_credentials(self):
        r = anonymize("Database: postgresql://admin:secret123@db.example.com/mydb")
        assert "[URL_REDACTED]" in r.text
        assert "secret123" not in r.text
        assert "admin" not in r.text


class TestAnonymizeMixed:
    def test_message_with_multiple_pii(self):
        text = (
            "Hey @john, I'm getting an error on 192.168.1.50. "
            "Send logs to debug@company.com. "
            "My key is sk-test12345678901234567890"
        )
        r = anonymize(text)
        assert "john" not in r.text
        assert "192.168.1.50" not in r.text
        assert "debug@company.com" not in r.text
        assert "sk-test" not in r.text
        assert r.redaction_count >= 4

    def test_code_block_preserved(self):
        """Code content should still be present (only PII redacted)."""
        text = "Try this:\n```python\ndef hello():\n    print('world')\n```"
        r = anonymize(text)
        assert "def hello():" in r.text
        assert "print('world')" in r.text

    def test_empty_string(self):
        r = anonymize("")
        assert r.text == ""
        assert r.redaction_count == 0


class TestAnonymizeBatch:
    def test_batch(self):
        results = anonymize_batch(["Email: a@b.com", "No PII", "IP: 10.0.0.1"])
        assert len(results) == 3
        assert results[0].redaction_count == 1
        assert results[1].redaction_count == 0
        assert results[2].redaction_count == 1
