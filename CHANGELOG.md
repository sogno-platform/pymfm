# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed
- Refactored optimization algorithm: split monolithic `optimization_based.py` into a structured `optimization/` package (`model`, `constraints`, `scheduler`, `solver`)
- Refactored service storage layer: replaced `crud.py`, `crud_fs.py`, `crud_memory.py`, `crud_redis.py` with a `storage/` package using a common base interface
- Renamed `data_aux.py` to `models.py` and replaced `single_job.py` with `balancing.py` router
- Consolidated utility modules: replaced `data_input.py`, `data_output.py`, `mode_logic_handler.py` with `data_prep.py` and `visualization.py`
- Added `control/schemas/` package with explicit `input.py` and `output.py` Pydantic schemas
- Added abstract base classes for algorithms (`algorithms/base.py`)
- Added central config module (`config.py`)
- Bumped minimum Python version from 3.8 to 3.10
- Updated core dependencies: pandas 1.5 → 2.3, pyomo 6.5 → 6.10, pydantic 2.7 → 2.12, fastapi 0.111 → 0.135, redis 4.5 → 7.4
