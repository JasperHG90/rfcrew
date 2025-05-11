import pathlib as plb
from typing import Any
import logging

from crewai import Agent, Task, Crew, Process, TaskOutput
from crewai.tools import BaseTool
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool

from rfcrew.utils import read_yaml

logger = logging.getLogger('rfcrew.crew')


def get_tools() -> dict[str, BaseTool]:
    return {
        'serper_dev_tool': SerperDevTool(),
        'scrape_website_tool': ScrapeWebsiteTool(),
        'website_search_tool': WebsiteSearchTool(
            config=dict(
                llm=dict(
                    provider='google',  # or google, openai, anthropic, llama2, ...
                    config=dict(
                        model='gemini-2.5-flash-preview-04-17',
                    ),
                ),
                embedder=dict(
                    provider='google',  # or openai, ollama, ...
                    config=dict(
                        model='models/embedding-004',
                        task_type='retrieval_document',
                    ),
                ),
            )
        ),
    }


def post_output_callback(output: TaskOutput):
    logger.debug(f'Finished task for agent "{output.agent}".')
    logger.debug(f'Output: {output.raw}')


class RFCrew:
    def __init__(
        self,
        tasks: dict[str, Any],
        agents: dict[str, Any],
        tools: dict[str, BaseTool],
        verbose: bool = False,
    ):
        self.tasks = tasks
        self.agents = agents
        self.tools = tools
        self.verbose = verbose

    @staticmethod
    def _parse_agent_config(
        agents_config: dict[str, Any], tools: dict[str, BaseTool]
    ) -> dict[str, Agent]:
        agents = {}
        for agent_name, agent_config in agents_config.items():
            if 'tools' in agent_config:
                _tools = [tools[tool_name.strip()] for tool_name in agent_config.pop('tools')]
            else:
                _tools = []
            agents[agent_name] = Agent(**agent_config, tools=_tools)
        return agents

    @staticmethod
    def _parse_task_config(
        tasks_config: dict[str, Any], agents: dict[str, Agent]
    ) -> dict[str, Task]:
        tasks = {}
        for task_name, task_config in tasks_config.items():
            _agent = agents[task_config.pop('agent').strip()]
            if 'context' in task_config:
                _context = [tasks[context] for context in task_config.pop('context')]
            else:
                _context = []
            tasks[task_name] = Task(
                agent=_agent, context=_context, callback=post_output_callback, **task_config
            )
        return tasks

    @classmethod
    def from_config(
        cls, agents_config_path: plb.Path, tasks_config_path: plb.Path, tools: dict[str, BaseTool]
    ) -> 'RFCrew':
        logger.info(
            f'Creating RFCrew from config files: agents={agents_config_path}, tasks={tasks_config_path}'
        )
        agents = cls._parse_agent_config(agents_config=read_yaml(agents_config_path), tools=tools)
        tasks = cls._parse_task_config(tasks_config=read_yaml(tasks_config_path), agents=agents)
        logger.info('RFCrew created from config.')
        return cls(agents=agents, tasks=tasks, tools=tools)

    def crew(self, planning: bool = True, planning_llm: str | None = None) -> Crew:
        logger.info(f'Creating Crew with planning={planning}, planning_llm={planning_llm}')
        crew = Crew(
            tasks=list(self.tasks.values()),
            agents=list(self.agents.values()),
            process=Process.sequential,
            verbose=self.verbose,
            planning=planning,
            planning_llm=planning_llm,
        )
        logger.info('Crew created.')
        return crew
