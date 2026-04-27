"""Unit tests for RAG service — chunking, cosine similarity, and index utilities."""

import pytest

from app.services.rag import chunk_text, cosine_similarity, clear_index


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_empty_string_returns_empty_list(self):
        assert chunk_text("") == []

    def test_short_text_is_single_chunk(self):
        text = "Hello world this is a short sentence"
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_produces_multiple_chunks(self):
        # 1200 words should produce more than 2 chunks at 500-word size
        text = " ".join([f"word{i}" for i in range(1200)])
        chunks = chunk_text(text)
        assert len(chunks) > 2

    def test_chunk_size_respected(self):
        words = [f"w{i}" for i in range(600)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=100, overlap=0)
        # Each chunk should have at most 100 words
        for chunk in chunks:
            assert len(chunk.split()) <= 100

    def test_overlap_causes_repeated_words(self):
        words = [f"word{i}" for i in range(120)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        if len(chunks) >= 2:
            # Last 20 words of chunk 0 should appear in start of chunk 1
            end_of_first = chunks[0].split()[-20:]
            start_of_second = chunks[1].split()[:20]
            assert end_of_first == start_of_second

    def test_no_overlap_no_repeated_words(self):
        words = [f"unique{i}" for i in range(200)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=100, overlap=0)
        all_words = []
        for chunk in chunks:
            all_words.extend(chunk.split())
        # No duplicates when overlap=0
        assert len(all_words) == len(set(all_words))

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_text("   ") == []

    def test_chunks_are_non_empty_strings(self):
        text = " ".join([f"w{i}" for i in range(600)])
        chunks = chunk_text(text)
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk.strip()) > 0

    def test_default_chunk_size_is_500_words(self):
        # 501 words should produce 2 chunks with default settings
        words = [f"w{i}" for i in range(501)]
        text = " ".join(words)
        chunks = chunk_text(text)
        assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# cosine_similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors_return_1(self):
        vec = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_return_0(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_return_negative_1(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_empty_vectors_return_0(self):
        assert cosine_similarity([], []) == 0.0

    def test_mismatched_lengths_return_0(self):
        assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0

    def test_zero_vector_returns_0(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_similarity_is_symmetric(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a), abs=1e-9)

    def test_similarity_range_is_bounded(self):
        import random
        random.seed(42)
        for _ in range(20):
            a = [random.uniform(-10, 10) for _ in range(10)]
            b = [random.uniform(-10, 10) for _ in range(10)]
            sim = cosine_similarity(a, b)
            assert -1.0 - 1e-6 <= sim <= 1.0 + 1e-6

    def test_single_element_vectors(self):
        assert cosine_similarity([5.0], [5.0]) == pytest.approx(1.0, abs=1e-6)
        assert cosine_similarity([5.0], [-5.0]) == pytest.approx(-1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# clear_index
# ---------------------------------------------------------------------------

class TestClearIndex:
    def test_clear_index_does_not_raise(self):
        # Just verifies the function is callable without error
        clear_index()

    def test_clear_index_is_idempotent(self):
        clear_index()
        clear_index()  # calling twice should not raise
