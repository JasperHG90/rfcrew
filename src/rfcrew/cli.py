import socket
import logging
from typing import Annotated
import pathlib as plb

import typer
import tenacity
from pydantic import BaseModel, AfterValidator

from rfcrew import __version__
from rfcrew.commands import generate_rfc_from_notes, evaluate_rfc_against_ground_truth


logger = logging.getLogger('rfcrew')
# handler = logging.StreamHandler()
# format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(format)
# logger.addHandler(handler)
# logger.setLevel(logging.INFO)


app = typer.Typer(
	help='🧰 A crew of AI agents for creating Requests for Comments (RFCs).',
	no_args_is_help=True,
)


@tenacity.retry(
	wait=tenacity.wait_exponential(multiplier=1, min=1, max=5),
	stop=tenacity.stop_after_attempt(5),
	retry=tenacity.retry_if_exception_type(ConnectionError),
)
def _ping_oltp_endpoint(v: str | None) -> str | None:
	if v is None:
		return None
	else:
		logger.debug(f'Checking OpenTelemetry endpoint: {v}')
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(3)
		try:
			host, port = v.rsplit(':')
			sock.connect((host, port))
			return v
		except socket.error as e:
			raise ConnectionError(f'Could not connect to OpenTelemetry endpoint: {e}')


class Common(BaseModel):
	verbose: bool
	output_directory: plb.Path
	otlp_endpoint: Annotated[str | None, AfterValidator(_ping_oltp_endpoint)]


@app.command(short_help='📌 Displays the current version number of the promptcreator library')
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
			envvar='RFCREW_OUTPUT_DIRECTORY',
		),
	] = plb.Path.cwd(),
	verbose: Annotated[
		bool, typer.Option(help='Enable debug logging.', envvar='RFCREW_VERBOSE')
	] = False,
	otlp_endpoint: Annotated[
		str | None, typer.Option(help='OpenLit endpoint', envvar='OTEL_EXPORTER_OTLP_ENDPOINT')
	] = None,
):
	if verbose:
		logger.setLevel(logging.DEBUG)
	if otlp_endpoint is not None:
		import openlit

		openlit.init(otlp_endpoint=otlp_endpoint)
	ctx.obj = Common(
		verbose=verbose, output_directory=output_directory, otlp_endpoint=otlp_endpoint
	)


@app.command(short_help='Generate a request for comments (RFC) from notes.')
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
	_output = generate_rfc_from_notes(
		path_to_notes=path_to_notes, agents_config=agents_config, tasks_config=tasks_config
	)
	logger.info('RFC generation complete.')


@app.command(short_help='Evaluate the generated RFC against a human-written RFC.')
def evaluate(
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
	logger.info('RFC evaluation complete.')


def entrypoint():
	app()
