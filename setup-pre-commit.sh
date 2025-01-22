# !/usr/bin/env bash

echo "Installing python dev dependencies"
pip install -r dev-requirements.txt

echo "Installing nodejs dev dependencies"
yarn install --frozen-lockfile --dev

echo "Setting up pre-commit hooks"
pre-commit install

echo "Setting up commit-msg hooks"
pre-commit install -t commit-msg

echo "Setup complete"