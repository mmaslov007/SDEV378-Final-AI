import unittest

from study_assistant.retrieval import HashingEmbedder, InMemoryVectorStore, build_index, chunk_text


class RetrievalTests(unittest.TestCase):
    def test_chunk_text_uses_overlap(self):
        text = " ".join(f"word{i}" for i in range(12))

        chunks = chunk_text(text, "notes", chunk_size=5, overlap=2)

        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0].metadata["start_word"], 0)
        self.assertEqual(chunks[1].metadata["start_word"], 3)
        self.assertIn("word3", chunks[0].text)
        self.assertIn("word3", chunks[1].text)

    def test_in_memory_vector_store_returns_relevant_chunk(self):
        chunks = chunk_text(
            "OCR reads scanned images. Embeddings retrieve source chunks. LLMs generate quizzes.",
            "study-notes",
            chunk_size=4,
            overlap=0,
        )
        store = InMemoryVectorStore(embedder=HashingEmbedder())
        store.add_chunks(chunks)

        results = store.query("semantic embeddings retrieval", limit=1)

        self.assertEqual(len(results), 1)
        self.assertIn("Embeddings retrieve", results[0].chunk.text)

    def test_build_index_can_use_dependency_free_fallback(self):
        store, chunks, warnings = build_index(
            "Retrieval augmented generation uses source snippets.",
            "notes",
            prefer_chroma=False,
        )

        self.assertEqual(store.backend_name, "in-memory")
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
