import logging
import os
from typing import Any

from pydantic import BaseModel, Field
from crewai import LLM, CrewOutput, Agent, Task, Crew

logger = logging.getLogger('rfcrew.crews.evaluator')


class EvaluationAgentModel(BaseModel):
	score: int = Field(..., description='Score from 1 (Very Different) to 10 (Very Similar)')
	justification: str = Field(..., description='Justification for the score')


class EvaluationAgent:
	def __init__(self, model: str):
		self._model = model

	@property
	def _llm(self):
		return LLM(model=self._model, temperature=0.2, api_key=os.environ.get('GEMINI_API_KEY'))

	@property
	def _agent(self) -> Agent:
		return Agent(
			role='RFC Solution Analyst',
			goal='To objectively evaluate and compare the core solutions proposed for similarity',
			backstory='You have a keen analytical mind and years of experience cutting through jargon and stylistic variations '
			'to get to the heart of technical proposals and descriptions. You understand that the same goal can be achieved in '
			'many ways, and your talent lies in pinpointing exactly how different approaches align or diverge in their fundamental '
			"mechanics, assumptions, or outcomes. You're not easily swayed by fancy formatting or persuasive language; you focus "
			'purely on the what and how of the proposed solution.',
			llm=self._llm,
		)

	@property
	def _task(self) -> Task:
		return Task(
			agent=self._agent,
			description='Your primary task is to take two documents provided as input. You need to carefully read and understand '
			'the solution being described or proposed in each one. Once you grasp the core concepts of both solutions, '
			'you will first assign a similarity score on a scale of 1 to 10, where 1 means the solutions are completely '
			'different and 10 means they describe the exact same solution. Second, you must write a concise report that '
			'clearly outlines the key differences between the solutions themselves, focusing on aspects like methodology, '
			'components, process steps, or expected outcomes, rather than differences in writing style, tone, or document '
			'structure.'
			'\n\nDocument 1: {document_1}'
			'\n---'
			'\n\nDocument 2: {document_2}',
			expected_output=(
				"A 'EvaluationAgentModel' object containing:\n"
				'1. `score`: An integer (1-10) representing the similarity of the described solution. Here, 1 means very dissimilar, '
				'and 10 means very similar.\n'
				'2. `justification`: A string explaining the reasoning behind the assigned score, highlighting strengths and weaknesses '
				'based on the evaluation criteria. Also explain how the two solutions differ.'
			),
			output_pydantic=EvaluationAgentModel,
		)

	@property
	def _crew(self) -> Crew:
		return Crew(agents=[self._agent], tasks=[self._task])

	def execute(self, inputs: dict[str, Any]) -> CrewOutput:
		logger.info(f'Executing EvaluationAgent with inputs: {inputs}')
		output = self._crew.kickoff(
			inputs=inputs,
		)
		logger.info(f'EvaluationAgent output: {output}')
		return output
