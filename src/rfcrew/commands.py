import logging
from typing import cast
import pathlib as plb

from crewai import CrewOutput

from .flows import RFCFlow, RFCFlowState
from .crews.evaluator import EvaluationAgent, EvaluationAgentModel
from .crews.assessor import ScoreAgentOutputModel, ScoreAgent
from .crews.converter import ConverterAgent

logger = logging.getLogger('rfcrew.commands')


def _configure_otlp_endpoint(v: str | None) -> None:
    if v is not None:
        import openlit

        openlit.init(otlp_endpoint=v)


def score_notes(
    path_to_notes: plb.Path,
    otlp_endpoint: str | None = None,
) -> ScoreAgentOutputModel:
    """
    Score the provided notes using the ScoreAgent.
    """
    _configure_otlp_endpoint(otlp_endpoint)
    logger.info(f'Starting scoring of notes: {path_to_notes}')
    with path_to_notes.open('r') as f:
        notes = f.read()

    logger.debug('Initializing ScoreAgent')
    agent = ScoreAgent(model='gemini/gemini-2.5-flash-preview-04-17')

    logger.debug('Executing ScoreAgent')
    result = agent.execute(
        inputs={
            'notes': notes.rstrip(),
        }
    )
    logger.info('Scoring completed successfully.')
    return cast(ScoreAgentOutputModel, result.pydantic)


def generate_rfc_from_notes(
    path_to_notes: plb.Path,
    agents_config: plb.Path,
    tasks_config: plb.Path,
    planning_llm: str | None = None,
    otlp_endpoint: str | None = None,
) -> tuple[RFCFlowState, None | CrewOutput]:
    """
    Generate an RFC from the provided notes.
    """
    _configure_otlp_endpoint(otlp_endpoint)
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
            'planning_llm': planning_llm,
        }
    )
    logger.info('RFC generation completed successfully.')
    return flow.state, result


def compare_documents(
    path_to_rfc: plb.Path,
    path_to_ground_truth: plb.Path,
    otlp_endpoint: str | None = None,
) -> EvaluationAgentModel:
    _configure_otlp_endpoint(otlp_endpoint)
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


def convert_rfc_to_adr(
    path_to_rfc: plb.Path,
    otlp_endpoint: str | None = None,
) -> str:
    _configure_otlp_endpoint(otlp_endpoint)
    logger.info(f'Converting RFC: {path_to_rfc}')
    logger.debug('Initializing EvaluationAgent')
    agent = ConverterAgent(model='gemini/gemini-2.5-flash-preview-04-17')

    logger.debug(f'Reading RFC file: {path_to_rfc}')
    with path_to_rfc.open('r') as f:
        rfc_doc = f.read()

    logger.debug('Executing converter agent')
    result = agent.execute({'RFC_content': rfc_doc})
    logger.info('RFC evaluation completed successfully.')
    return result.raw
