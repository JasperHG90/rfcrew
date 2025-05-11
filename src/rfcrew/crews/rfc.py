import os
import logging
import pathlib as plb
from typing import Any

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool

from rfcrew.utils import read_yaml

logger = logging.getLogger('rfcrew.crews.rfc')


def get_tools() -> dict[str, BaseTool]:
    logger.info('Initializing tools...')
    tools = {
        'serper_dev_tool': SerperDevTool(),
        'scrape_website_tool': ScrapeWebsiteTool(),
        'website_search_tool': WebsiteSearchTool(
            config=dict(
                llm=dict(
                    provider='google',  # or google, openai, anthropic, llama2, ...
                    config=dict(
                        model='gemini-2.5-flash-preview-04-17',
                        api_key=os.environ.get('GOOGLE_API_KEY'),
                    ),
                ),
                embedder=dict(
                    provider='google',  # or openai, ollama, ...
                    config=dict(
                        model='models/embedding-004',
                        task_type='retrieval_document',
                        # google_api_key=os.environ.get('GOOGLE_API_KEY'),
                    ),
                ),
            )
        ),
    }
    logger.info(f'Initialized {len(tools)} tools.')
    logger.debug(f'Tools available: {list(tools.keys())}')
    return tools


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
        logger.info(f'Parsing {len(agents_config)} agent configurations.')
        agents = {}
        try:
            for agent_name, agent_config in agents_config.items():
                logger.debug(f'Parsing agent: {agent_name}')
                agent_tools_config = agent_config.pop('tools', [])
                _tools = [tools[tool_name.strip()] for tool_name in agent_tools_config]
                llm_config = agent_config.pop('llm')
                _llm = LLM(
                    model=llm_config, temperature=0.2, api_key=os.environ.get('GOOGLE_API_KEY')
                )
                agents[agent_name] = Agent(**agent_config, tools=_tools, llm=_llm)
            logger.info(f'Successfully parsed {len(agents)} agents.')
            logger.debug(f'Parsed agents: {list(agents.keys())}')
            return agents
        except KeyError as e:
            logger.exception(
                f"Error parsing agent config: Tool '{e}' not found in available tools."
            )
            raise
        except Exception:
            logger.exception('Failed to parse agent configurations.')
            raise

    @staticmethod
    def _parse_task_config(
        tasks_config: dict[str, Any], agents: dict[str, Agent]
    ) -> dict[str, Task]:
        logger.info(f'Parsing {len(tasks_config)} task configurations.')
        tasks = {}
        try:
            for task_name, task_config in tasks_config.items():
                logger.debug(f'Parsing task: {task_name}')
                agent_name = task_config.pop('agent').strip()
                _agent = agents[agent_name]
                context_tasks = task_config.pop('context', [])
                _context = [tasks[context_task_name.strip()] for context_task_name in context_tasks]
                tasks[task_name] = Task(agent=_agent, context=_context, **task_config)
            logger.info(f'Successfully parsed {len(tasks)} tasks.')
            logger.debug(f'Parsed tasks: {list(tasks.keys())}')
            return tasks
        except KeyError as e:
            logger.exception(f"Error parsing task config: Agent or Context Task '{e}' not found.")
            raise
        except Exception:
            logger.exception('Failed to parse task configurations.')
            raise

    @classmethod
    def from_config(
        cls, agents_config_path: plb.Path, tasks_config_path: plb.Path, tools: dict[str, BaseTool]
    ) -> 'RFCrew':
        logger.info(
            f'Creating RFCrew from config files: agents="{agents_config_path}", tasks="{tasks_config_path}"'
        )
        logger.debug(f'Reading agent config from: {agents_config_path}')
        agents_config = read_yaml(agents_config_path)
        agents = cls._parse_agent_config(agents_config=agents_config, tools=tools)

        logger.debug(f'Reading task config from: {tasks_config_path}')
        tasks_config = read_yaml(tasks_config_path)
        tasks = cls._parse_task_config(tasks_config=tasks_config, agents=agents)

        logger.info('RFCrew created successfully from config.')
        return cls(agents=agents, tasks=tasks, tools=tools)

    def crew(self, planning_llm: str | None = None) -> Crew:
        logger.info(
            f'Creating Crew with planning={True if planning_llm else False}, planning_llm={planning_llm}'
        )
        crew = Crew(
            tasks=list(self.tasks.values()),
            agents=list(self.agents.values()),
            process=Process.sequential,
            verbose=self.verbose,
            planning=False if not planning_llm else True,
            planning_llm=LLM(
                model=planning_llm,
                temperature=0.2,
                # Apparently, we need to specify `google_api_key` here as well
                #  ...
                # How on earth does this work?
                api_key=os.environ.get('GOOGLE_API_KEY'),
                google_api_key=os.environ.get('GOOGLE_API_KEY'),
            )
            if planning_llm
            else None,
        )
        logger.info('Crew created.')
        return crew
