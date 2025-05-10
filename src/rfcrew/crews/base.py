import logging
import os
from abc import ABC, abstractmethod
from typing import Any

from crewai import LLM, CrewOutput, Agent, Task, Crew

logger = logging.getLogger('rfcrew.crews.base')


class BaseAgent(ABC):
	def __init__(self, model: str):
		self._model = model

	@property
	def _llm(self):
		return LLM(model=self._model, temperature=0.2, api_key=os.environ.get('GOOGLE_API_KEY'))

	@property
	@abstractmethod
	def _agent(self) -> Agent: ...

	@property
	@abstractmethod
	def _task(self) -> Task: ...

	@property
	def _crew(self) -> Crew:
		return Crew(agents=[self._agent], tasks=[self._task])

	def execute(self, inputs: dict[str, Any]) -> CrewOutput:
		logger.info(
			f'Starting {self.__class__} execution with inputs: {list(inputs.keys())}'
		)  # Log only keys for brevity
		logger.debug('Kicking off crew')
		output = self._crew.kickoff(
			inputs=inputs,
		)
		logger.info(f'Agent "{self.__class__}" execution completed successfully.')
		logger.debug(f'{self.__class__} raw output: {output}')  # Add debug log for raw output
		return output
