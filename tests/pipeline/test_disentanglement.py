"""Tests for the Disentanglement Engine."""

from datetime import datetime, timedelta

from api.services.extraction.disentanglement import DisentanglementEngine, RawMessage


class TestDisentanglement:
    def setup_method(self):
        self.engine = DisentanglementEngine()

    def test_empty_input(self):
        assert self.engine.cluster([]) == []

    def test_single_message(self):
        msg = RawMessage(id="1", author_hash="a", content="hello", timestamp=datetime.now())
        result = self.engine.cluster([msg])
        assert len(result) == 1
        assert len(result[0]) == 1

    def test_separates_greetings_from_tech(self, sample_messages):
        threads = self.engine.cluster(sample_messages)
        # Should produce at least 2 threads (greetings vs tech)
        assert len(threads) >= 2

        # Find the tech thread (contains "ENOMEM")
        tech_threads = [t for t in threads if any("ENOMEM" in m.content for m in t)]
        assert len(tech_threads) == 1
        tech = tech_threads[0]

        # Tech thread should have 4 messages
        assert len(tech) == 4

        # Should contain the solution confirmation
        assert any("worked" in m.content for m in tech)

    def test_reply_to_forces_link(self):
        now = datetime.now()
        messages = [
            RawMessage(id="1", author_hash="a", content="How to fix error X?", timestamp=now),
            RawMessage(id="2", author_hash="b", content="Totally unrelated topic about cooking", timestamp=now + timedelta(minutes=1)),
            RawMessage(id="3", author_hash="c", content="Try solution Y for that error", timestamp=now + timedelta(minutes=2), reply_to="1"),
        ]
        threads = self.engine.cluster(messages)
        # Message 1 and 3 should be in the same thread (reply_to link)
        for t in threads:
            ids = {m.id for m in t}
            if "1" in ids:
                assert "3" in ids, "reply_to should link messages 1 and 3"
                break

    def test_mention_forces_link(self):
        now = datetime.now()
        messages = [
            RawMessage(id="1", author_hash="alice", content="I have a Python import error", timestamp=now),
            RawMessage(id="2", author_hash="bob", content="Random chat message", timestamp=now + timedelta(minutes=1)),
            RawMessage(id="3", author_hash="charlie", content="@alice try checking your PYTHONPATH", timestamp=now + timedelta(minutes=2), mentions=["alice"]),
        ]
        threads = self.engine.cluster(messages)
        for t in threads:
            ids = {m.id for m in t}
            if "1" in ids:
                assert "3" in ids, "@mention should link messages"
                break

    def test_temporal_window_respected(self):
        now = datetime.now()
        messages = [
            RawMessage(id="1", author_hash="a", content="How to configure webpack?", timestamp=now),
            RawMessage(id="2", author_hash="b", content="How to configure webpack properly?", timestamp=now + timedelta(hours=5)),
        ]
        threads = self.engine.cluster(messages)
        # Should be in separate threads (>4h apart, despite similar content)
        assert len(threads) == 2

    def test_threads_sorted_by_timestamp(self, sample_messages):
        threads = self.engine.cluster(sample_messages)
        for thread in threads:
            timestamps = [m.timestamp for m in thread]
            assert timestamps == sorted(timestamps), "Messages within thread should be sorted by timestamp"
