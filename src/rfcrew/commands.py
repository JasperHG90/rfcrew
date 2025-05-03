import logging
from typing import cast
import pathlib as plb

from .flows import RFCFlow
from .crews.evaluator import EvaluationAgent, EvaluationAgentModel

logger = logging.getLogger('rfcrew.commands')


def generate_rfc_from_notes(
	path_to_notes: plb.Path,
	agents_config: plb.Path,
	tasks_config: plb.Path,
):
	"""
	Generate an RFC from the provided notes.
	"""
	logger.info(f'Generating RFC from notes: {path_to_notes}')
	flow = RFCFlow(
		agents_config_path=agents_config,
		tasks_config_path=tasks_config,
	)
	with path_to_notes.open('r') as f:
		notes = f.read()
	result = flow.kickoff(inputs={'notes': notes.rstrip()})
	logger.info('RFC generation complete.')
	return result


def evaluate_rfc_against_ground_truth(
	path_to_rfc: plb.Path,
	path_to_ground_truth: plb.Path,
) -> EvaluationAgentModel:
	logger.info(f'Evaluating RFC: {path_to_rfc} against ground truth: {path_to_ground_truth}')
	agent = EvaluationAgent(model='gemini/gemini-2.5-flash-preview-04-17')
	with path_to_rfc.open('r') as f:
		rfc_doc = f.read()
	with path_to_ground_truth.open('r') as f:
		ground_truth_doc = f.read()
	result = agent.execute({'document_1': rfc_doc, 'document_2': ground_truth_doc})
	logger.info('RFC evaluation complete.')
	return cast(EvaluationAgentModel, result.pydantic)
