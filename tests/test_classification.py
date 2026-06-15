import unittest
from types import SimpleNamespace

from study_assistant.classification import DIFFICULTIES, classify_document


class FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeGroqClient:
    def __init__(self, content):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


SAMPLE_TEXT = (
    "Embeddings convert text into vectors for semantic retrieval. "
    "Embeddings power similarity search. ChromaDB stores embeddings and retrieves "
    "the closest chunks for a query."
)


class ClassificationTests(unittest.TestCase):
    def test_heuristic_topics_and_difficulty_without_api_key(self):
        tags = classify_document(SAMPLE_TEXT, api_key="")

        self.assertFalse(tags.used_llm)
        self.assertIn(tags.difficulty, DIFFICULTIES)
        self.assertTrue(tags.has_topics)
        self.assertIn("Embeddings", tags.topics)

    def test_empty_text_returns_default_medium(self):
        tags = classify_document("   ", api_key="")

        self.assertEqual(tags.difficulty, "medium")
        self.assertFalse(tags.has_topics)
        self.assertEqual(tags.metadata["method"], "none")

    def test_llm_path_uses_returned_topics_and_difficulty(self):
        content = '{"topics": ["Embeddings", "Vector Search"], "difficulty": "hard"}'

        tags = classify_document(SAMPLE_TEXT, client=FakeGroqClient(content))

        self.assertTrue(tags.used_llm)
        self.assertEqual(tags.topics, ["Embeddings", "Vector Search"])
        self.assertEqual(tags.difficulty, "hard")

    def test_llm_invalid_difficulty_falls_back_to_heuristic_value(self):
        content = '{"topics": ["Embeddings"], "difficulty": "impossible"}'

        tags = classify_document(SAMPLE_TEXT, client=FakeGroqClient(content))

        self.assertIn(tags.difficulty, DIFFICULTIES)
        self.assertNotEqual(tags.difficulty, "impossible")


if __name__ == "__main__":
    unittest.main()
