import logging
from typing import cast
import pathlib as plb

from crewai import CrewOutput

from .flows import RFCFlow, RFCFlowState
from .crews.evaluator import EvaluationAgent, EvaluationAgentModel

logger = logging.getLogger('rfcrew.commands')


def generate_rfc_from_notes(
	path_to_notes: plb.Path,
	agents_config: plb.Path,
	tasks_config: plb.Path,
) -> tuple[RFCFlowState, None | CrewOutput]:
	"""
	Generate an RFC from the provided notes.
	"""
	logger.info(f'Starting RFC generation from notes: {path_to_notes}')
	with path_to_notes.open('r') as f:
		notes = f.read()

	logger.debug('Initializing RFCFlow')
	flow = RFCFlow()
	logger.debug('Kicking off RFCFlow')
	result = flow.kickoff(
		inputs={
			'notes': notes.rstrip(),
			'agents_config_path': agents_config,
			'tasks_config_path': tasks_config,
		}
	)
	logger.info('RFC generation completed successfully.')
	return flow.state, result


def evaluate_rfc_against_ground_truth(
	path_to_rfc: plb.Path,
	path_to_ground_truth: plb.Path,
) -> EvaluationAgentModel:
	logger.info(
		f'Starting evaluation of RFC: {path_to_rfc} against ground truth: {path_to_ground_truth}'
	)
	logger.debug('Initializing EvaluationAgent')
	agent = EvaluationAgent(model='gemini/gemini-2.5-flash-preview-04-17')

	logger.debug(f'Reading RFC file: {path_to_rfc}')
	with path_to_rfc.open('r') as f:
		rfc_doc = f.read()
	logger.debug(f'Reading ground truth file: {path_to_ground_truth}')
	with path_to_ground_truth.open('r') as f:
		ground_truth_doc = f.read()

	logger.debug('Executing evaluation agent')
	result = agent.execute({'document_1': rfc_doc, 'document_2': ground_truth_doc})
	logger.info('RFC evaluation completed successfully.')
	return cast(EvaluationAgentModel, result.pydantic)
