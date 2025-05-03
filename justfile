alias s := setup
alias t := test
alias p := pre_commit

# Default arg for openlit docker-compose
default := 'up'

# Install python dependencies
install:
  uv sync

# Install pre-commit hooks
pre_commit_setup:
  uv run pre-commit install

# Install python dependencies and pre-commit hooks
setup: install pre_commit_setup

# Run pre-commit
pre_commit:
 uv run pre-commit run -a

# Run pytest
test:
  uv run pytest tests

# Start openlit
openlit cmd=default:
  #!/bin/bash
  if [ ! -d "openlit" ]; then
    echo "Creating openlit directory..."
    mkdir openlit
  else
    echo "openlit directory already exists."
  fi

  # Download the docker-compose.yml file
  if [ ! -f "openlit/docker-compose.yml" ]; then
    echo "Downloading docker-compose.yml..."
    curl -o openlit/docker-compose.yml https://raw.githubusercontent.com/openlit/openlit/refs/heads/main/docker-compose.yml
  else
    echo "docker-compose.yml already exists."
  fi

  if [ ! -d "openlit/assets" ]; then
    echo "Creating openlit/assets directory..."
    mkdir openlit/assets
  else
    echo "openlit/assets directory already exists."
  fi

  # Download the otel-collector-config.yaml file
  if [ ! -f "openlit/assets/otel-collector-config.yaml" ]; then
    echo "Downloading otel-collector-config.yaml..."
    curl -o openlit/assets/otel-collector-config.yaml https://raw.githubusercontent.com/openlit/openlit/refs/heads/main/assets/otel-collector-config.yaml
  else
    echo "otel-collector-config.yaml already exists."
  fi

  echo "{{cmd}}"

  if [ "{{ cmd }}" == "up"  ]; then
    echo "Running docker-compose up..."
    docker-compose -f openlit/docker-compose.yml up -d
  elif [ "{{ cmd }}" == "down" ]; then
    echo "Running docker-compose down..."
    docker-compose -f openlit/docker-compose.yml down
  else
    echo "Invalid argument. Use 'up' or 'down'."
  fi
