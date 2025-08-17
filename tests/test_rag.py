import pytest


@pytest.mark.skip(reason="RAG endpoints removed in new API version")
def test_rag_removed():
    assert True
