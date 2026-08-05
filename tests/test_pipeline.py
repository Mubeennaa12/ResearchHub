"""
TODO: once agents/retrieval have real implementations, add:
- Unit tests per agent with mocked Anthropic client responses
- An integration test that runs Pipeline.run() against a fixture
  knowledge base with known documents, asserting the answer cites the
  right source and the retrieval loop terminates within max_retrieval_loops
- A regression test for the citation checker: feed it a draft answer with
  a deliberately unsupported claim and confirm it gets flagged
"""

import pytest


def test_placeholder():
    # Replace once Pipeline has a working implementation.
    assert True
