import pathlib as plb

import pytest

from rfcrew.cli import Common


def test_common_model_passes(tmp_path: plb.Path):
    """Test the Common model."""
    # Create an instance of the Common model with test data
    Common(verbose=True, output_directory=tmp_path, otlp_endpoint=None)


def test_common_model_with_bad_oltp(tmp_path: plb.Path):
    """Test the Common model with a bad otlp endpoint."""
    # Create an instance of the Common model with test data
    with pytest.raises(ConnectionError):
        Common(
            verbose=True, output_directory=tmp_path, otlp_endpoint='http://bad-otel-collector:4318'
        )
