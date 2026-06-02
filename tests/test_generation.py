import unittest
from types import SimpleNamespace

from study_assistant.generation import _parse_json_object, generate_study_output
from study_assistant.retrieval import SearchResult, SourceChunk


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


def sample_results():
    chunks = [
        SourceChunk(
            id="c1",
            text="Embeddings convert text into vectors for semantic retrieval.",
            source_name="notes",
            chunk_index=0,
        ),
        SourceChunk(
            id="c2",
            text="OCR turns images of text into readable strings.",
            source_name="notes",
            chunk_index=1,
        ),
    ]
    return [SearchResult(chunk=chunk, score=0.9) for chunk in chunks]


class GenerationTests(unittest.TestCase):
    def test_parse_json_object_handles_fenced_json(self):
        parsed = _parse_json_object('```json\n{"title": "Quiz", "items": []}\n```')

        self.assertEqual(parsed["title"], "Quiz")

    def test_generate_uses_fake_groq_client_and_normalizes_items(self):
        content = """
        {
          "title": "Embedding Quiz",
          "items": [
            {
              "question": "What do embeddings create?",
              "choices": ["Vectors", "Images", "Keys", "Tables"],
              "answer": "Vectors",
              "explanation": "The source says embeddings convert text into vectors.",
              "sources": ["S1"]
            }
          ]
        }
        """
        output = generate_study_output(
            mode="quiz",
            topic="embeddings",
            results=sample_results(),
            client=FakeGroqClient(content),
        )

        self.assertEqual(output.title, "Embedding Quiz")
        self.assertTrue(output.used_llm)
        self.assertEqual(output.items[0].answer, "Vectors")
        self.assertEqual(output.items[0].sources, ["S1"])

    def test_missing_api_key_returns_transparent_fallback(self):
        output = generate_study_output(
            mode="flashcards",
            topic="OCR",
            results=sample_results(),
            api_key="",
        )

        self.assertFalse(output.used_llm)
        self.assertIn("GROQ_API_KEY", output.warnings[0])
        self.assertGreaterEqual(len(output.items), 1)


if __name__ == "__main__":
    unittest.main()
