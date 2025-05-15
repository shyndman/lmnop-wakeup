#!/usr/bin/env bash

uv tool run ruff check --fix
uv tool run ruff format
