# RFCrew

> [!WARNING]
> This library is in development. Use at your own risk.

A crew of AI agents for creating and evaluating Requests for Comments (RFCs). This project uses CrewAI to orchestrate agents that can generate RFCs from notes. You can also compare two RFCs for similarity.

![Crew](./assets/RFCrew.png)

## Rationale

Writing RFCs can take a lot of work. If a AI agents can produce the first 50-60% of the document then we can spend more time on implementation.

> [!WARNING]
> This is AI-generated content. Small changes in the input notes can make a large difference. And of course: actually read the output instead of taking it at face value.

## How it works

### Crews

There are three crews defined in this library.

#### RFCrew

This crew generates an RFC from input notes. The AI agents defined for this task are:

* **RFC Research Assistant**: Research topics that serve as input to create Request for Comments (RFC) documents
... continue copy-paste from config/agents.yaml

#### Scorer

This is a single-agent crew that scores the input notes for completion. It assigns a score from 1-10 and provides a brief justification for the score.

The agent definition can be found in `src/rfcrew/crews/assessor.py`

#### Evaluator

This is a single-agent crew that compares two RFCs, in particular w.r.t. the solution described. It provides a similarity score from 1-10 and a brief justification. You can use this to check the consistency between two generated RFCs.

The agent definition can be found in `src/rfcrew/crews/evaluator.py`

### Flow

When you call the entrypoint with `generate` command, the following flow is executed.

![Flow](assets/crewai_flow_static.png)

First, your input notes are scored. If they are not sufficient, the feedback and score are printed and the flow exits. If the notes are sufficient, then an RFC is generated.

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

If you're using the devcontainer (or have UV installed), you can execute:

```bash
uv sync
```

### Configuration Files

The behavior of the RFC generation crew is controlled by two YAML configuration files:

*   `config/agents.yaml`: Defines the agents, their roles, goals, backstories, and the tools they can use.
*   `config/tasks.yaml`: Defines the tasks the agents will perform, their descriptions, and the agent assigned to each task.

Examples of these configuration files can be found in the `config/` directory.

### Dev Container

This project includes a Dev Container configuration for easy setup of a development environment with all necessary dependencies. If you are using VS Code and have the Dev Containers extension installed, you will be prompted to reopen the project in the container. This will automatically install the required dependencies and set up the environment.

### OpenLit

To keep track of the LLM calls, costs, and other metrics and debugging info, you can execute `just openlit up`. This downloads the [openlit](https://github.com/openlit/openlit) docker-compose YAML and runs `docker-compose up`.

Metrics are tracked automatically with OpenLit via OpenTelemetry if you run a CLI command with the `--otlp-endpoint` callback, e.g.

```bash
uv run rfcrew \
    --otlp-endpoint=http://127.0.0.1:4318
    ...
```

The dashboard is available at: http://127.0.0.1:3000

Credentials:

- Email: user@openlit.io
- Password: openlituser

Execute `just openlit down` to shut down openlit.

### Justfile

The project includes a `justfile` with several commands to simplify common development tasks. You can list available commands by running `just` in the terminal. Some of the commonly used commands include:

*   `just install`: Installs python dependencies using uv.
*   `just setup`/`just s`: Installs python dependencies and sets up pre-commit hooks.
*   `just test`/`just t`: Runs pytest tests.
*   `just pre_commit`/`just p`: Runs pre-commit checks.
*   `just openlit <up>/<down>`: downloads and sets up [OpenLit](https://github.com/openlit/openlit)

### Setting up your Gemini key

Set the `GOOGLE_API_KEY` environment variable with your Gemini API key. Get the key [here](https://ai.google.dev/).

```bash
export GOOGLE_API_KEY='YOUR_API_KEY'
```

If you're using the devcontainer, you should store this environment variable in `.devcontainer/.env`

### Setting up your Serper key

This library uses the [Serper](https://serper.dev/) API so that the RFC crew can execute Google searches. You need an account (it comes with a generous free tier) and API key.

The API key should be exported as an environment variable called `SERPER_API_KEY`:

```bash
export SERPER_API_KEY="YOUR_API_KEY"
```

If you're using the devcontainer, you should store this environment variable in `.devcontainer/.env`

### Commands

Type `rfcrew --help` to view available commands and global arguments (e.g. otlp endpoint, output directory, verbose output)

## Examples

The 'samples' directory contains sample notes and RFC outputs.

### Scoring input notes

You can score input notes using `rfcrew score`:

```bash
uv run rfcrew \
    score \
    "/home/vscode/workspace/samples/bq_write_api/notes/bq_write_api_insufficient.md"
```

Output:

```
Score: 5
Feedback: The notes provide a clear topic, scope, and a good list of requirements and constraints. The background and context are sufficient to understand the motivation. However, the problem definition could be sharper, focusing more on the specific challenges of using the BQ Write API with Python/Protobuf rather than just stating the need to find the 'best way'. Crucially, there is no evidence of initial research or exploration of potential approaches/alternatives, which is a significant gap for an RFC kick-off. This lack of preliminary investigation necessitates a score below 6.
```

### Generating an RFC draft

To generate an RFC draft, use the `generate` command. You need to pass the input path to the notes as well as the agents and tasks configuration.

```bash
uv run rfcrew \
    --verbose \
    --otlp-endpoint=http://127.0.0.1:4318 \
    generate \
    "/home/vscode/workspace/samples/notes/bq_write_api_sufficient.md" \
    --agents-config="/home/vscode/workspace/config/agents.yaml" \
    --tasks-config="/home/vscode/workspace/config/tasks.yaml"
```

These two agents and tasks configuration files location can be set using environment variables `RFCREW_AGENTS_CONFIG` and `RFCREW_TASKS_CONFIG` respectively.

If you're using the devcontainer, you can place these environment variables in your .devcontainer/.env file.

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
