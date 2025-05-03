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
	# Add config locations here
	agents_config_path: plb.Path = Field(..., description='Path to the agents configuration file')
	tasks_config_path: plb.Path = Field(..., description='Path to the tasks configuration file')
	notes: str = Field(default='', description='Initial notes provided for the RFC process')
	notes_feedback: ScoreAgentOutputModel | None = Field(
		default=None, description='Feedback from the ScoreAgent on the RFC notes'
	)


class RFCFlow(Flow[RFCFlowState]):
	@start()
	def score(self) -> ScoreAgentOutputModel:
		logger.info('Starting score function.')
		scorer = ScoreAgent(model='gemini/gemini-2.5-flash-preview-04-17')
		output = scorer.execute({'notes': self.state.notes})

		self.state.notes_feedback = cast(ScoreAgentOutputModel, output.pydantic)
		logger.info(f'Score: {self.state.notes_feedback.score}')
		return self.state.notes_feedback

	@router(score)
	def process_score(self, scorer_output: ScoreAgentOutputModel) -> str:
		logger.info(f'Processing score: {scorer_output.score}')
		if scorer_output.score <= 6:
			logger.info('Score is not OK.')
			return 'not_OK'
		else:
			logger.info('Score is OK.')
			return 'OK'

	@listen('not_OK')
	def not_ok(self) -> None:
		logger.info('Notes are not OK.')
		logger.info('The input notes are not sufficient to proceed with the RFC process.')
		logger.info(
			f'Feedback: {cast(ScoreAgentOutputModel, self.state.notes_feedback).justification}'
		)
		logger.info('Please provide more detailed notes.')

	@listen('OK')
	def ok(self) -> CrewOutput:
		logger.info('Notes are OK.')
		print('The input notes are sufficient to proceed with the RFC process.')
		_crew = RFCrew.from_config(
			agents_config_path=plb.Path(self.state.agents_config_path),
			tasks_config_path=plb.Path(self.state.tasks_config_path),
			tools=get_tools(),
		).crew()
		logger.info('Kicking off crew.')
		return _crew.kickoff({'notes': self.state.notes})
