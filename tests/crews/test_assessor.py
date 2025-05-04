import pytest
from unittest.mock import patch, MagicMock, ANY
import os

# Assuming crewai and pydantic are installed and available
from crewai import Agent, Task, Crew, CrewOutput, LLM

# Import the classes to be tested
from src.rfcrew.crews.assessor import ScoreAgent, ScoreAgentOutputModel


# Mock the LLM class entirely for all tests in this module
@pytest.fixture(autouse=True)
def mock_llm():
	with patch('src.rfcrew.crews.assessor.LLM', autospec=True) as mock:
		# Configure the mock LLM instance if needed, e.g., mock.return_value.some_method.return_value = ...
		yield mock


@pytest.fixture
def score_agent():
	"""Provides a ScoreAgent instance for testing."""
	# Set a dummy API key for testing purposes if the code checks for it
	with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'}):
		return ScoreAgent(model='test-model')


def test_score_agent_init(score_agent):
	"""Test ScoreAgent initialization."""
	assert score_agent._model == 'test-model'


def test_score_agent_llm_property(score_agent, mock_llm):
	"""Test the _llm property."""
	llm_instance = score_agent._llm
	assert isinstance(llm_instance, LLM)
	# Check if LLM was called with expected args (using the mock)
	mock_llm.assert_called_once_with(model='test-model', temperature=0.2, api_key='test_key')


@patch('src.rfcrew.crews.assessor.Agent', autospec=True)
def test_score_agent_agent_property(mock_agent_class, score_agent):
	"""Test the _agent property."""
	agent_instance = score_agent._agent
	assert isinstance(agent_instance, Agent)
	# Check if Agent was called with expected args
	mock_agent_class.assert_called_once_with(
		role='RFC Readiness Analyst',
		goal=ANY,  # Check specific goal string if needed
		backstory=ANY,  # Check specific backstory string if needed
		llm=score_agent._llm,  # It uses the potentially mocked LLM instance
	)


@patch('src.rfcrew.crews.assessor.Task', autospec=True)
def test_score_agent_task_property(mock_task_class, score_agent):
	"""Test the _task property."""
	# Need to mock the agent property call within the task property
	with patch.object(ScoreAgent, '_agent', new_callable=MagicMock) as mock_agent_prop:
		mock_agent_instance = MagicMock(spec=Agent)
		mock_agent_prop.return_value = mock_agent_instance

		task_instance = score_agent._task
		assert isinstance(task_instance, Task)
		# Check if Task was called with expected args
		mock_task_class.assert_called_once_with(
			agent=mock_agent_instance,
			description=ANY,  # Check specific description string if needed
			expected_output=ANY,  # Check specific expected_output string if needed
			output_pydantic=ScoreAgentOutputModel,
		)


@patch('src.rfcrew.crews.assessor.Crew', autospec=True)
def test_score_agent_crew_property(mock_crew_class, score_agent):
	"""Test the _crew property."""
	# Need to mock agent and task properties
	with (
		patch.object(ScoreAgent, '_agent', new_callable=MagicMock) as mock_agent_prop,
		patch.object(ScoreAgent, '_task', new_callable=MagicMock) as mock_task_prop,
	):
		mock_agent_instance = MagicMock(spec=Agent)
		mock_task_instance = MagicMock(spec=Task)
		mock_agent_prop.return_value = mock_agent_instance
		mock_task_prop.return_value = mock_task_instance

		crew_instance = score_agent._crew
		assert isinstance(crew_instance, Crew)
		# Check if Crew was called with expected args
		mock_crew_class.assert_called_once_with(
			agents=[mock_agent_instance], tasks=[mock_task_instance]
		)


@patch('src.rfcrew.crews.assessor.Crew', autospec=True)
@patch('src.rfcrew.crews.assessor.logger', autospec=True)  # Mock logger
def test_score_agent_execute(mock_logger, mock_crew_class, score_agent):
	"""Test the execute method."""
	# Mock the crew instance and its kickoff method
	mock_crew_instance = MagicMock(spec=Crew)
	mock_output = MagicMock(spec=CrewOutput)
	mock_crew_instance.kickoff.return_value = mock_output
	mock_crew_class.return_value = mock_crew_instance  # Crew() returns our mock

	# Mock the _crew property to return our mock instance directly
	with patch.object(ScoreAgent, '_crew', new_callable=MagicMock) as mock_crew_prop:
		mock_crew_prop.return_value = mock_crew_instance

		test_inputs = {'notes': 'Some initial notes for the RFC.'}
		result = score_agent.execute(inputs=test_inputs)

		# Assertions
		mock_logger.info.assert_any_call(
			f'Starting ScoreAgent execution with inputs: {list(test_inputs.keys())}'
		)
		mock_logger.debug.assert_any_call('Kicking off scoring crew')
		mock_crew_instance.kickoff.assert_called_once_with(inputs=test_inputs)
		mock_logger.info.assert_any_call('ScoreAgent execution completed successfully.')
		mock_logger.debug.assert_any_call(f'ScoreAgent raw output: {mock_output}')
		assert result == mock_output
