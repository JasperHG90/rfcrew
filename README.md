# RFCrew

> [!WARNING]
> This library is in development. Use at your own risk.

A crew of AI agents for creating and evaluating Requests for Comments (RFCs). This project uses CrewAI to orchestrate agents that can generate RFCs from notes. You can also compare two RFCs for similarity.

![Crew](./assets/RFCrew.png)

## Features

*   **RFC Generation:** Generate RFCs from provided notes using a configurable crew of agents.
*   **RFC Evaluation:** Evaluate a generated RFC against a human-written ground truth.
*   **Configurable Agents and Tasks:** Define agent roles, goals, backstories, and tasks using YAML configuration files.
*   **Tool Usage:** Agents can utilize tools like web search and web scraping to gather information.
*   **Notes Scoring:** Initial notes are scored for sufficiency before proceeding with RFC generation.

## Caution

This is AI-generated content. Small changes in the input notes can make a large difference.

## Usage

### Installation

First, clone the repository:

```bash
git clone https://github.com/your_username/rfcrew.git # Replace with the actual repository URL
cd rfcrew
```

(Assuming the project is installable via pip)

```bash
pip install .
```

### Setting up your Gemini key

Set the `GOOGLE_API_KEY` environment variable with your Gemini API key.

```bash
export GOOGLE_API_KEY='YOUR_API_KEY'
```

### Configuring the CLI

The CLI can be configured using environment variables or command-line options.

*   `RFCREW_OUTPUT_DIRECTORY`: Specifies the output directory for generated files (default: current working directory).
*   `RFCREW_VERBOSE`: Enables debug logging.
*   `RFCREW_AGENTS_CONFIG`: Path to the agents configuration file (required for `generate` command).
*   `RFCREW_TASKS_CONFIG`: Path to the tasks configuration file (required for `generate` command).

### Commands

#### `rfcrew generate`

Generates a Request for Comments (RFC) from notes using a crew of agents.

```bash
rfcrew generate <path_to_notes> --agents-config <path_to_agents_config> --tasks-config <path_to_tasks_config>
```

*   `<path_to_notes>`: Path to the input notes file.
*   `--agents-config`: Path to the agents configuration YAML file.
*   `--tasks-config`: Path to the tasks configuration YAML file.

#### `rfcrew evaluate`

Evaluates a generated RFC against a human-written ground truth.

```bash
rfcrew evaluate <path_to_rfc> <path_to_ground_truth>
```

*   `<path_to_rfc>`: Path to the generated RFC file.
*   `<path_to_ground_truth>`: Path to the ground truth RFC file.

### Configuration Files

The behavior of the RFC generation crew is controlled by two YAML configuration files:

*   `config/agents.yaml`: Defines the agents, their roles, goals, backstories, and the tools they can use.
*   `config/tasks.yaml`: Defines the tasks the agents will perform, their descriptions, and the agent assigned to each task.

Examples of these configuration files can be found in the `config/` directory.

### Dev Container

This project includes a Dev Container configuration for easy setup of a development environment with all necessary dependencies. If you are using VS Code and have the Dev Containers extension installed, you will be prompted to reopen the project in the container. This will automatically install the required dependencies and set up the environment.

### Justfile

The project includes a `justfile` with several commands to simplify common development tasks. You can list available commands by running `just` in the terminal. Some of the commonly used commands include:

*   `just install`: Installs python dependencies using uv.
*   `just setup`: Installs python dependencies and sets up pre-commit hooks.
*   `just test`: Runs pytest tests.
*   `just pre_commit`: Runs pre-commit checks.

## Limitations

Currently, only Gemini models are supported.

Mermaid syntax is often a bit off.

## For later

- Add memory capabilities
    * [Mem0](https://mem0.ai/)

- Allow user full control over models (also for e.g. planning)
- Testing setup
- Mermaid MCP syntax checking server
- Tweak models used to set up the crew
- More models
