import pytest

from rfcrew.crews.assessor import ScoreAgent


@pytest.fixture
def score_agent() -> ScoreAgent:
	"""Provides a ScoreAgent instance for testing."""
	return ScoreAgent(model='gemini/gemini-2.5-flash-preview-04-17')


@pytest.mark.llm
def test_score_agent_execute(score_agent: ScoreAgent):
	"""Test the execute method of ScoreAgent."""
	# Mock input data
	input_data = {'notes': 'This is a test note.'}

	# Execute the agent
	score_agent.execute(input_data)
