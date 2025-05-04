import logging
from typing import cast
import pathlib as plb

from pydantic import BaseModel, Field
from crewai import CrewOutput
from crewai.flow.flow import Flow, listen, start, router

from rfcrew.crews.assessor import ScoreAgentOutputModel, ScoreAgent
from rfcrew.crews.rfc import RFCrew, get_tools

logger = logging.getLogger('rfcrew.flows')


class RFCFlowState(BaseModel):
	agents_config_path: plb.Path = Field(
		default='', description='Path to the agents configuration file'
	)
	tasks_config_path: plb.Path = Field(
		default='', description='Path to the tasks configuration file'
	)
	notes: str = Field(default='', description='Initial notes provided for the RFC process')
	notes_feedback: ScoreAgentOutputModel | None = Field(
		default=None, description='Feedback from the ScoreAgent on the RFC notes'
	)


class RFCFlow(Flow[RFCFlowState]):
	@start()
	def score(self) -> ScoreAgentOutputModel:
		logger.debug('Starting initial notes scoring.')
		logger.debug('Initializing ScoreAgent.')
		scorer = ScoreAgent(model='gemini/gemini-2.5-flash-preview-04-17')
		logger.debug('Executing ScoreAgent.')
		output = scorer.execute({'notes': self.state.notes})

		self.state.notes_feedback = cast(ScoreAgentOutputModel, output.pydantic)
		logger.debug(f'Notes scoring completed. Score: {self.state.notes_feedback.score}')
		logger.debug(f'ScoreAgent raw output: {output}')
		return self.state.notes_feedback

	@router(score)
	def process_score(self, scorer_output: ScoreAgentOutputModel) -> str:
		logger.debug(f'Processing score: {scorer_output.score}')
		if scorer_output.score <= 6:
			logger.info('Score is not OK.')
			return 'not_OK'
		else:
			logger.info('Score is OK.')
			return 'OK'

	@listen('not_OK')
	def not_ok(self) -> None:
		logger.debug('The input notes are not sufficient to proceed with the RFC process.')
		logger.debug(
			f'Feedback: {cast(ScoreAgentOutputModel, self.state.notes_feedback).justification}'
		)
		logger.info('Please provide more detailed notes.')

	@listen('OK')
	def ok(self) -> CrewOutput:
		logger.debug('Notes score is OK. Proceeding with RFC generation.')
		logger.debug('Creating RFCrew from config.')
		_crew_builder = RFCrew.from_config(
			agents_config_path=self.state.agents_config_path,
			tasks_config_path=self.state.tasks_config_path,
			tools=get_tools(),
		)
		logger.debug('Building Crew instance.')
		_crew = _crew_builder.crew(
			planning=True, planning_llm='gemini/gemini-2.5-flash-preview-04-17'
		)

		logger.debug('Kicking off RFC generation crew.')
		result = _crew.kickoff({'notes': self.state.notes})
		logger.debug('RFC generation crew finished successfully.')
		logger.debug(f'RFC crew raw output: {result}')
		return result
