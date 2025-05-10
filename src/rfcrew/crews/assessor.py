from pydantic import BaseModel, Field
from crewai import Agent, Task

from .base import BaseAgent


class ScoreAgentOutputModel(BaseModel):
	score: int = Field(
		..., description='Score from 1 (Very Vague/Incomplete) to 10 (Very Clear/Comprehensive)'
	)
	justification: str = Field(..., description='Justification for the score')


class ScoreAgent(BaseAgent):
	@property
	def _agent(self) -> Agent:
		return Agent(
			role='RFC Readiness Analyst',
			goal='To evaluate and score the quality and completeness of the initial input notes '
			"provided for generating an RFC, ensuring there's enough information to proceed "
			'effectively.',
			backstory='You believe in pausing before diving headfirst into drafting an RFC. You question whether '
			'the initial requester provided enough information to proceed effectively, having seen too many '
			'cycles wasted chasing vague ideas. Your job is to quickly assess the initial prompt: Is the '
			'problem clear? Are the boundaries defined? Are there any hard requirements or explicit constraints? '
			'Has any prior thought gone into this? You understand that a quick score helps set expectations and '
			'encourages better input quality in the future.',
			llm=self._llm,
		)

	@property
	def _task(self) -> Task:
		return Task(
			agent=self._agent,
			description=(
				'**Goal:** You need to evaluate the quality and completeness of initial notes '
				'provided for generating a Request for Comments (RFC). Your goal is to assess if the notes form a sufficiently '
				'solid foundation for the RFC process.\n\n'
				'**Evaluation Criteria:** Analyze the provided notes based on the following key aspects. The presence and clarity '
				'of *each* aspect contribute to the overall quality:\n'
				'1.  **Topic Clarity & Scope:** Is the main topic of the proposed RFC clearly stated? Is the scope defined and '
				'appropriately limited?\n'
				'2.  **Background & Context:** Is there adequate background information explaining the circumstances, motivations, '
				'or existing situation relevant to the RFC?\n'
				'3.  **Problem Definition:** Is the specific problem that the RFC intends to solve clearly articulated and justified?\n'
				'4.  **Requirements & Constraints:** Are essential technical or non-technical requirements mentioned? Are any '
				"important constraints (e.g., 'must integrate with system X', 'cannot use technology Y', budget limitations) specified?\n"
				'5.  **Initial Research / Alternatives:** Do the notes show evidence of preliminary thinking or research? Are any potential '
				'alternative solutions or approaches mentioned, even if briefly?\n\n'
				'**Task:** Based on your analysis against *all* the above criteria:\n'
				'   - Assign a holistic quality score from 1 (Very Vague/Incomplete) to 10 (Very Clear/Comprehensive).\n'
				'   - Provide a concise justification explaining the score. Reference specific criteria that are strong or weak.\n'
				'If any of the criteria missing entirely, you MUST assign a score below 6.'
				'A high score requires reasonable clarity and detail across **ALL** criteria.'
				'**Input:** You will receive raw text notes intended to kickstart an RFC ({notes})'
			),
			expected_output=(
				"A 'ScoreAgentOutputModel' object containing:\n"
				'1. `score`: An integer (1-10) representing the overall readiness and quality of the input notes for RFC generation.\n'
				'2. `justification`: A string explaining the reasoning behind the assigned score, highlighting strengths and weaknesses based on the evaluation criteria.'
			),
			output_pydantic=ScoreAgentOutputModel,
		)
