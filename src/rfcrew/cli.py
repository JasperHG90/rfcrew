import socket
import logging
from typing import Annotated, cast
import pathlib as plb

from rich import print
import typer
import tenacity
import coolname
from pydantic import BaseModel, AfterValidator

from rfcrew import __version__
from rfcrew.crews.assessor import ScoreAgentOutputModel
from rfcrew.commands import generate_rfc_from_notes, evaluate_rfc_against_ground_truth, score_notes


logger = logging.getLogger('rfcrew')


app = typer.Typer(
	help='🧰 A crew of AI agents for creating Requests for Comments (RFCs).',
	no_args_is_help=True,
)


def _ping_oltp_endpoint(v: str | None) -> str | None:
	if v is not None:
		logger.info('Pinging OpenTelemetry endpoint...')
	for attempt in tenacity.Retrying(
		wait=tenacity.wait_exponential(multiplier=1, min=1, max=5),
		stop=tenacity.stop_after_attempt(5),
		retry=tenacity.retry_if_exception_type(ConnectionError),
		reraise=True,
	):
		with attempt:
			logger.debug(
				f'Attempting to ping OpenTelemetry endpoint (attempt {attempt.retry_state.attempt_number})...'
			)
			if v is None:
				return None
			else:
				logger.debug(f'Checking OpenTelemetry endpoint: {v}')
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.settimeout(3)
				try:
					if v.startswith('http') or v.startswith('https'):
						v = v.replace('http://', '').replace('https://', '')
					address, port = v.rsplit(':')
					logger.debug(f'Parsed address: {address}, port: {port}')
					sock.connect((address, int(port)))
					logger.debug(f'Connected to OpenTelemetry endpoint: {v}')
					return v
				except socket.error as e:
					raise ConnectionError(f'Could not connect to OpenTelemetry endpoint "{v}": {e}')


class Common(BaseModel):
	verbose: bool
	output_directory: plb.Path
	otlp_endpoint: Annotated[str | None, AfterValidator(_ping_oltp_endpoint)] = None


@app.command(short_help='Displays the current version number of the rfcrew library')
def version():
	print(__version__)


@app.callback()
def main(
	ctx: typer.Context,
	output_directory: Annotated[
		plb.Path,
		typer.Option(
			help='Output directory for files created using this application',
			exists=True,
			file_okay=False,
			dir_okay=True,
			resolve_path=True,
		),
	] = plb.Path.cwd(),
	verbose: Annotated[bool, typer.Option(help='Enable debug logging.')] = False,
	otlp_endpoint: Annotated[str | None, typer.Option(help='OpenLit endpoint')] = None,
):
	if verbose:
		logger.setLevel(logging.DEBUG)
	if otlp_endpoint is not None:
		import openlit

		openlit.init(otlp_endpoint=otlp_endpoint)
	ctx.obj = Common(
		verbose=verbose, output_directory=output_directory, otlp_endpoint=otlp_endpoint
	)


@app.command(
	short_help='Score input notes and receive feedback on quality and completeness',
	no_args_is_help=True,
)
def score(
	ctx: typer.Context,
	path_to_notes: Annotated[
		plb.Path,
		typer.Argument(
			help='Path to the notes file',
			exists=True,
			file_okay=True,
			dir_okay=False,
			resolve_path=True,
		),
	],
):
	logger.info(f'Scoring notes: {path_to_notes}')
	result = score_notes(path_to_notes=path_to_notes)
	_score = f'[red]{result.score}[/red]' if result.score < 6 else f'[green]{result.score}[/green]'
	print(f'[bold]Score:[/bold] {_score}')
	print(f'[bold]Feedback:[/bold] {result.justification}')


@app.command(short_help='Generate a request for comments (RFC) from notes.', no_args_is_help=True)
def generate(
	ctx: typer.Context,
	path_to_notes: Annotated[
		plb.Path,
		typer.Argument(
			help='Path to the notes file',
			exists=True,
			file_okay=True,
			dir_okay=False,
			resolve_path=True,
		),
	],
	agents_config: Annotated[
		plb.Path,
		typer.Option(
			help='Path to the agents configuration file',
			exists=True,
			file_okay=True,
			dir_okay=False,
			resolve_path=True,
			envvar='RFCREW_AGENTS_CONFIG',
		),
	],
	tasks_config: Annotated[
		plb.Path,
		typer.Option(
			help='Path to the tasks configuration file',
			exists=True,
			file_okay=True,
			dir_okay=False,
			resolve_path=True,
			envvar='RFCREW_TASKS_CONFIG',
		),
	],
):
	logger.info(f'Generating RFC from notes: {path_to_notes}')
	_uid = coolname.generate_slug(2).replace('-', '_')
	state, output = generate_rfc_from_notes(
		path_to_notes=path_to_notes, agents_config=agents_config, tasks_config=tasks_config
	)
	if output is None:
		print(
			f'[bold]Score:[/bold] [red]{cast(ScoreAgentOutputModel, state.notes_feedback).score}[/red]'
		)
		print(
			f'[bold]Feedback:[/bold] {cast(ScoreAgentOutputModel, state.notes_feedback).justification}'
		)
	else:
		shared = cast(Common, ctx.obj)
		with (shared.output_directory / f'rfc_{_uid}.md').open('w') as generated_rfc:
			raw_mkd: str = output.raw
			# Post-process the raw markdown to remove code blocks
			if raw_mkd.startswith('```markdown'):
				raw_mkd = raw_mkd.lstrip('```markdown').lstrip('\n')
			if raw_mkd.endswith('```'):
				raw_mkd = raw_mkd.rstrip('```').rstrip('\n')
			generated_rfc.write(raw_mkd)
		logger.info('RFC generation complete.')


@app.command(
	short_help='Compare two documents for similarity on described solution', no_args_is_help=True
)
def compare(
	path_to_rfc: Annotated[
		plb.Path,
		typer.Argument(
			help='Path to the notes file',
			exists=True,
			file_okay=True,
			dir_okay=False,
			resolve_path=True,
		),
	],
	path_to_ground_truth: Annotated[
		plb.Path,
		typer.Argument(
			help='Path to the notes file',
			exists=True,
			file_okay=True,
			dir_okay=False,
			resolve_path=True,
		),
	],
):
	logger.info(f'Evaluating RFC: {path_to_rfc} against ground truth: {path_to_ground_truth}')
	_output = evaluate_rfc_against_ground_truth(
		path_to_ground_truth=path_to_ground_truth, path_to_rfc=path_to_rfc
	)
	print('Evaluation results:')
	print('[bold]Score:[/bold] ', _output.score)
	print('[bold]Feedback:[/bold]: ', _output.justification)
	logger.info('RFC evaluation complete.')


def entrypoint():
	app()
