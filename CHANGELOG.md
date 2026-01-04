## 1.5.0 (2025-12-23)

### Feat

- **worker-manager**: implement child process termination on macOS/BSD
- **worker-manager**: terminate child processes with parent
- **cli**: add modular CLI and rich interactive menu
- **logging**: set logging directory for funcnodes_core in StandaloneLauncher

### Refactor

- **tests**: migrate tests from unittest to pytest in test_cmd.py and test_worker_manager.py
- **tests**: further migrate test examples to pytest syntax
- **tests**: remove obsolete unittest test file
- **tests**: migrate from unittest to pytest for test examples

## 1.4.0 (2025-12-18)

### Feat

- **docs**: add experimental features section and standalone mode documentation
- **standalone**: add --register to set .fnw file opener
- **standalone**: add in_venv parameter to StandaloneLauncher and enhance worker startup logic
- **worker**: add command subtask to invoke exposed methods
- **server**: enhance browser opening functionality with fallbacks
- **scripts**: add Windows launcher and file association for .fnw files
- **standalone**: implement standalone task and launcher
- **server**: add worker configuration options and endpoint
- **docs**: add mkdocs-llmstxt plugin and update site URL

### Fix

- **tests**: update launcher script assertions for cross-platform compatibility
- **tests**: enhance shutdown handling in standalone tests
- **tests**: update assertions in is_worker_running tests to return tuple format
- **worker**: handle error messages in worker command responses
- **standalone**: improve launcher shutdown and worker detection
- **runner**: make shutdown thread-safe and close active connections
- **cli**: gracefully shut down monitor on interrupt
- **worker**: handle asyncio event loop initialization and improve logging

### Refactor

- **funcnodes**: decouple worker commands from argparse.Namespace

## 1.3.1 (2025-12-01)

### Fix

- correct package name in version retrieval

## 1.3.0 (2025-11-30)

### Feat

- add subprocess monitor argument to main function

### Fix

- update package version handling in __init__.py

## 1.2.0 (2025-11-05)

### Feat
- Bump funcnodes_worker dependency to version 1.2.0 for both emscripten and non-emscripten platforms in pyproject.toml and related lock files.
- Refactor data path handling in worker management and main application code to utilize worker_json_get_data_path for improved consistency and clarity.

## v1.1.1 (2025-10-22)

### Feat
- update project version to 1.1.1 and add LazyImport utility

## v1.1.0a0 (2025-10-21)

### Feat
- **worker-manager**: support deleting workers and align config access

### Chore
- update funcnodes_worker dependency and versioning
- update versioning and dependencies for funcnodes
- update venvmngr dependency to version 0.2.0 in pyproject.toml and uv.lock
- update dependencies and versioning across multiple files

## v1.0.2 (2025-09-03)

### Other
- Update version to 1.0.2 and adjust funcnodes-core dependency in pyproject.toml for compatibility improvements.

## v1.0.1 (2025-09-03)

### Other
- Introduce consistent sleep intervals in WorkerManager to prevent busy-waiting. Added await asyncio.sleep(0.5) in multiple locations to improve efficiency during worker readiness checks and configuration file validation.
- Add maximum wait time for worker connection in WorkerManager
- Refactor timeout condition in WorkerManager to ensure proper worker readiness checks. Updated logic to verify the existence of the worker configuration file before raising a timeout error.
- Enhance WorkerManager to improve worker configuration handling. Added checks for worker config, runstate, and process files to ensure proper worker readiness and UUID consistency before establishing a websocket connection.
- Update version to 1.0.1 and adjust funcnodes-core dependency in pyproject.toml for compatibility improvements.
- Update funcnodes-react-flow dependency version in pyproject.toml to 1.0.0 for improved compatibility.
- Refactor code for improved readability and consistency. Cleaned up whitespace and formatting in multiple files, including examples, main module, worker manager, and test cases.
- Implement connection timeout and runstate monitoring in WorkerManager. Added logic to check for worker readiness and handle timeouts, improving error handling during worker activation.

## v1.0.0 (2025-08-29)

### Other
- Enhance pytest configuration for asyncio support and update test setup. Added asyncio mode settings in pytest.ini and configured test environment in TestExamples class to handle warnings.
- uv lock fix
- Refactor test_cmd.py to dynamically include FUNCNODES_CONFIG_DIR in command strings for improved flexibility in command generation
- update version to 1.0.0, adjust dependencies for funcnodes-core and funcnodes_worker, and enhance error handling in worker management

## v1.0.0a2 (2025-08-29)

### Other
- bump version to 1.0.0a2 and update funcnodes_worker dependencies to version 1.0.0a0 for improved compatibility

## v1.0.0a1 (2025-08-28)

### Other
- bump version to 1.0.0a1, update subprocess-monitor dependency to 0.3.0, and modify install script to include --refresh option

## v1.0.0a0 (2025-08-28)

### Other
- bump version to 1.0.0a0, update dependencies to latest versions, and switch build system to Hatchling for improved packaging
- add custom CSS for SVG icons and include in MkDocs configuration
- static update

## v0.5.37 (2025-03-28)

### Other
- bump version to 0.5.37 and update imports for consistency

## v0.5.36 (2025-03-26)

### Docs
- update README.md

### Other
- update funcnodes-react-flow dependency to version 0.4.1 for improved functionality
- bump version to 0.5.36 and update dependencies for improved compatibility
- refactor server configuration retrieval in add_runserver_parser for improved clarity and flexibility
- add pytest-funcnodes dependency for improved testing capabilities
- add screenshot to README.md for enhanced visual reference
- refactor worker handling in basic_funcnodes_pyodide.js; update event listener and adjust default dimensions
- refactor documentation and improve nodebuilder integration; add default Python editor code and enhance worker handling
- Aktualisieren von README.md
- add workerfile metadata to CSV and Titanic examples; update navigation in mkdocs
- convert fnw_url to lowercase in example_theme.html
- example update
- use dynamic base URL for SharedWorker paths in noderenderer.js
- to doc
- --profiling optional

## v0.5.35 (2025-02-14)

### Other
- emscripten support
- use default python executable in worker start arguments (the start process switches automatically)
- worker manager does not directly update, since this blocks, better do this in the worker process

## v0.5.34 (2025-02-10)

### Refactor
- remove unused files and update imports for funcnodes_worker integration

### Other
- bump version to 0.5.34 and update funcnodes_worker dependency

## v0.5.33 (2025-02-09)

### Other
- reorganize optional dependencies in pyproject.toml for clarity
- update dependencies and version; add documentation files to .gitignore
- add link to official Funcnodes documentation in README
- add custom JavaScript and CSS for NodeBuilder integration in documentation
- add introduction guide and example image for FuncNodes documentation
- add initial documentation files and UI guide for FuncNodes
- update GitHub Actions workflow to specify mkdocs configuration file for deployment
- update deployment command in GitHub Actions workflow to use 'uv run'
- add dependencies for MkDocs and MkDocs Material in pyproject.toml
- add GitHub Actions workflow for documentation deployment
- initialized docs
- format module listing output for better readability
- add support for 'modules' task in worker environment and streamline command execution
- refactor command execution in worker environment to use subprocess and improve logging
- not all tasks in subprocess monitor
- refactor progress messages in worker class to include dependency names

## v0.5.32 (2025-02-05)

### Other
- remove unnecessary serialization and deserialization in worker class
- increase timer loop threshold in external worker tests to 0.25 seconds

## v0.5.31 (2025-02-04)

### Other
- increase maximum default data size for Uploads application to 10GB

## v0.5.30 (2025-02-04)

### Other
- bump version to 0.5.30 and enhance profiling and command options

## v0.5.29 (2025-02-03)

### Other
- bump version to 0.5.29 and integrate yappi for profiling

## v0.5.28 (2025-02-03)

### Other
- profiling in main
- some debugging logs

## v0.5.27 (2025-01-31)

### Other
- string to bytes

## v0.5.26 (2025-01-31)

### Other
- import of workers with higher py version not failing by default

## v0.5.25 (2025-01-31)

### Other
- worker export and import with files
- logger in installing

## v0.5.24 (2025-01-30)

### Other
- some debugging logs

## v0.5.23 (2025-01-30)

### Other
- main options
- some debugging logs
- funcnodes react check
- coorect plugins lookup

## v0.5.21 (2025-01-30)

### Other
- via_subprocess_monitor stops on finish

## v0.5.20 (2025-01-30)

### Other
- assert worker manager running subscription in new task

## v0.5.19 (2025-01-29)

### Other
- version prefix check
- refresh error if underscore in worker name

## v0.5.18 (2025-01-29)

### Other
- logging and streamlining
- websockets to aiohttp since it is used already

## v0.5.17 (2025-01-28)

### Other
- funneling throug subprocess monitor

## v0.5.16 (2025-01-28)

### Other
- restruc
- runnning worker pid check
- pip assured inside

## v0.5.15 (2025-01-23)

### Other
- or to and

## v0.5.14 (2025-01-23)

### Other
- dont update  version if version is current version

## v0.5.13 (2025-01-23)

### Other
- dir arg for local dev
- exporting toml

## v0.5.12 (2025-01-21)

### Other
- uv worker managing

## v0.5.11 (2025-01-17)

### Other
- stop worker

## v0.5.10 (2025-01-13)

### Other
- always set files dir

## v0.5.9 (2025-01-12)

### Other
- vb
- ruff
- pathify

## v0.5.8 (2025-01-09)

### Other
- file upload

## v0.5.7 (2025-01-08)

### Other
- vb
- more secure json write
- not in venv worker
- updated websocket
- IN_NODE_TEST
- ws worker aiohhtp
- running prop type
- running helper
- int ports
- shutdown server

## v0.5.6 (2024-12-10)

### Other
- simple server kwargs

## v0.5.5 (2024-12-10)

### Other
- cmd maker helper

## v0.5.4 (2024-12-10)

### Other
- ws worker params from env

## v0.5.3 (2024-12-10)

### Other
- main update

## v0.5.2 (2024-12-09)

### Other
- python_path to calllist

## v0.5.1 (2024-12-09)

### Other
- log exception in main

## v0.5.0 (2024-12-09)

### Other
- licence
- default workertype
- logger update

## v0.4.47 (2024-12-05)

### Other
- vb
- start worker util
- typing
- change port

## v0.4.46 (2024-11-13)

### Other
- vb
- socket and queue worker
- default messages layout functions

## v0.4.45 (2024-11-11)

### Other
- updating dependencies with progess
- install dep contains name

## v0.4.44 (2024-11-11)

### Other
- vb
- ignore ws send exc
- fallback args kwargs in handler

## v0.4.43 (2024-11-11)

### Other
- formatting

## v0.4.42 (2024-11-11)

### Other
- vb
- manager less  blocking
- corrected caller list

## v0.4.41 (2024-11-11)

### Other
- WebSocketException

## v0.4.40 (2024-11-11)

### Other
- error msg

## v0.4.39 (2024-11-08)

### Other
- asyncification

## v0.4.38 (2024-11-08)

### Other
- external_worker in module

## v0.4.37 (2024-11-07)

### Other
- relaod repos on update

## v0.4.36 (2024-11-07)

### Other
- frontend update

## v0.4.35 (2024-11-07)

### Other
- updateing and exporting worker
- serialize external worker

## v0.4.34 (2024-11-05)

### Other
- workermanager logging

## v0.4.33 (2024-11-05)

### Other
- vb
- activating worker env
- listen worker and better creation
- env create new worker

## v0.4.32 (2024-11-05)

### Other
- vb
- dont reload base on module init

## v0.4.31 (2024-11-04)

### Other
- vb
- pid in config

## v0.4.30 (2024-11-04)

### Other
- wrong indent bug

## v0.4.29 (2024-11-04)

### Other
- raect flow update

## v0.4.28 (2024-11-04)

### Other
- simple sever
- subprocess_monitor

## v0.4.27 (2024-10-30)

### Other
- write pid to process_file
- vb
- auto stop when in subprocess
- print to log
- patch std for pipe
- localhost to ip

## v0.4.26 (2024-10-28)

### Other
- acknowledge runnong loop

## v0.4.25 (2024-10-28)

### Other
- run vs loop

## v0.4.24 (2024-10-28)

### Other
- env per worker

## v0.4.23 (2024-10-28)

### Other
- flow update

## v0.4.22 (2024-10-28)

### Other
- subprocess_monitor

## v0.4.21 (2024-10-23)

### Other
- signaturewrapper
- vb
- expose controlled_wrapper

## v0.4.20 (2024-10-22)

### Other
- setup not in init

## v0.4.19 (2024-10-19)

### Other
- vb
- input forward impl

## v0.4.18 (2024-10-19)

### Other
- removed core tests
- always src to trg
- removed cache py
- missing version update

## v0.4.17 (2024-10-11)

### Other
- correct default ws values

## v0.4.16 (2024-10-11)

### Other
- shelves_dependencies rem

## v0.4.15 (2024-10-08)

### Other
- temp hide test
- time barrier
- vb
- 3np1 trigger update
- worker update
- exports
- logo update
- readme update
- logo

## v0.4.13 (2024-09-27)

### Other
- worker update
- react dependency update

## v0.4.12 (2024-09-26)

### Other
- missing requests
- load libs

## v0.4.11 (2024-09-25)

### Other
- vb
- urls
- licence stuff
- shelves dep as dict

## v0.4.10 (2024-09-23)

### Other
- update test
- vb
- update_io_options  requests_save
- debug flag
- update_io_options

## v0.4.9 (2024-09-13)

### Other
- autosetup and version bump
- create dir if missing including parents
- print update

## v0.4.8 (2024-09-04)

### Other
- heatbeat

## v0.4.7 (2024-09-04)

### Other
- vb
- set_value events are preview encoded

## v0.4.6 (2024-09-03)

### Other
- test update missed
- vb
- get values

## v0.4.5 (2024-09-03)

### Other
- core update

## v0.4.4 (2024-08-30)

### Other
- wm ssl

## v0.4.3 (2024-08-30)

### Other
- vb
- server worker_manager_host
- workflow update

## v0.4.2 (2024-08-30)

### Other
- vb
- cleanup
- workermanager optioanl host and port

## v0.4.1 (2024-08-28)

### Other
- funcnodes_react_flow per default

## v0.4.0 (2024-08-28)

### Feat
- Initial release.
