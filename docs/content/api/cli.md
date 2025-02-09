# FuncNodes CLI Guide

The FuncNodes command-line interface (CLI) allows users to manage workflows, workers, and configurations efficiently. This guide provides an overview of available commands and usage examples.

---

## **Getting Started**

To check if FuncNodes is installed and accessible, run:

```bash
funcnodes --version
```

To view all available commands:

```bash
funcnodes --help
```

---

## **CLI Commands**

[runserver]: #runserver
[worker]: #worker
[workermanager]: #workermanager
[modules]: #modules
[commonoptions]: #commonoptions

### Common Options { #commonoptions}

The basic command structure for the CLI is:

```bash
funcnodes [common_options] {task}
```

where {task} specifies an operation. The shared common options for all tasks are:

<div class="annotate" markdown>
- `--version` → Prints the current version of FuncNodes.
- ` -h, --help ` →  Displays CLI help.
- `--dir <path>` → Specifies a custom base directory where workflow data is stored (default: `~/.funcnodes`). In this directory all configurations, logs, worker data, worker environments etc. is stored. So by defining a custom path it is possible to completly seperate instances of FuncNodes.
For development purposes we recomment setting `--dir .funcnodes` (1) which will create a respective folder in your current worspace.
- `--debug` →  Enables debugging logs for all processes (and child processes).
- `--profile` → Only available if FuncNodes was installed with the optional dependency `fundnodes[profiling]` Runs the task under profiling mode using [yappi](https://github.com/sumerc/yappi){target="_blank"}, generating a *funcnodesprofile.pstat* file in your current directory. This file than can be opened with different profiling views such as [snakeviz](https://jiffyclub.github.io/snakeviz/){target="_blank"}
</div>

1. This is also what `--funcnodes-module demoworker` does.

### Tasks

The `funcnodes` command expects a specific task, which can be one of the following:

- runserver → Runs the [browser interface](../ui-guide/react_flow/web-ui.md) with various [options][runserver]
- worker → Allows running and management of a [Worker](../components/worker.md)([options][worker])
- startworkermanager → Starts the [Workermanager](../components/workermanager.md)([options][workermanager])
- modules → Gives access to the installed FuncNodes modules ([options][modules])

#### runserver { #runserver}

To start the [FuncNodes web UI](../ui-guide/react_flow/web-ui.md), use:

```bash
funcnodes [common_options] runserver [server_options]
```

This will run a simple server that serves all the static static files necessary to use Funcnodes in the browser. By default the server runs on `localhost:8000` and a corresponding browser window is opened autoamtically. To interact with the [Workers](../components/worker.md) the server tries to find a running instance of a [Workermanager](../components/workermanager.md) under `localhost:9380` and if it cannot find a running instance it will spawn a new one.
Optional argument to the command are:

| Argument                            | Description                                                                                                                                                                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| --host                              | The host adress of the server, defaults to the [config](../components/config.md)["frontend"]["host"] (default:localhost)                                                                                                                  |
| --port                              | The port of the server, defaults to the [config](../components/config.md)["frontend"]["port"] (default:8000)                                                                                                                              |
| --no-browser                        | If present, does not open a browser window                                                                                                                                                                                                |
| --no-manager                        | The server does not automatically spawns a [Workermanager](../components/workermanager.md)                                                                                                                                                |
| <nobr>--worker_manager_host </nobr> | The host adress of the [Workermanager](../components/workermanager.md) the server tries to rach or under which a new one will be spawned, defaults to the [config](../components/config.md)["worker_manager"]["host"] (default:localhost) |
| <nobr>--worker_manager_port</nobr>  | The port of the [Workermanager](../components/workermanager.md) the server tries to rach or under which a new one will be spawned, defaults to the [config](../components/config.md)["worker_manager"]["port"] (default:9380)             |
| --frontend                          | Which frontend to use in the UI (currently only [`react_flow`](../ui-guide/react_flow/web-ui.md) is supported)                                                                                                                            |

#### worker { #worker}

The task command `worker` allows to create, start, stop and interact with the [Worker](../components/worker.md) instances of FuncNodes. The command is build up as:

```bash
funcnodes [common_options] worker [worker_options] workertask
```

where the worker_options are mainy to define which worker to acess:

| Argument | Description                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------------ |
| --uuid   | The unique id of the Worker, for a new worker it will be created automatically                         |
| --name   | The (non-unique) name of the Worker, for a new worker it defaults to the uuid but can be changed later |

To interact with an existing Worker either `--uuid` or `--name` have to be present. If only name is given the first worker with the given name will be picked (as it is not unqiue). For new Workers a if no `--uuid` is given, it will be created automatically and if `--name` is not set, it will be the `uuid` by default.

The command then requires a worker specific task:

- [new][worker_new] → Creates a new Worker
- [start][worker_start] → Runs the existing worker
- [stop][worker_stop] → Stops the existing, running worker
- [modules][worker_modules] → Runs the `funcnodes module` command in the Worker env
- [list][worker_list] → List all existing workers
- [listen][worker_listen] → Listens to the output of an existing worker
- [activate][worker_activate] → Activates the environment of an existing worker (if present)
- [py][worker_py] → Runs the Python instance of the respective worker

[worker_new]: #worker_new
[worker_start]: #worker_start
[worker_stop]: #worker_stop
[worker_list]: #worker_list
[worker_listen]: #worker_listen
[worker_activate]: #worker_activate
[worker_py]: #worker_py
[worker_modules]: #worker_modules

##### new worker { #worker_new}

To create a new worker via the CLI the basic command is:

```bash
funcnodes [common_options] worker [worker_options] new [new_worker_options]
```

This command creates a new worker in your current `<funcnodes directory>/worker` defined via the [common_options][commonoptions] (default `~/.funcnodes/worker`). If the uuid and name are not set in the [worker_options][worker] they will be created automatically.

The worker can be created with a bunch of creation options via `[new_worker_options]`:

| Argument                    | Description                                                                                                                                                                                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| --create-only               | By default a newly created worker will automatically start. By setting this flag it will only be created and not started                                                                                                                                         |
| --not-in-venv               | By default new workers will also create their own virtual environment in there respective path. By setting this flag the worker will be initiated with the current python interpreter (and always use this interpreter even if started from another environment) |
| <nobr>(--workertype)</nobr> | Defines the workertype (this feature is under development and should not be used currently)                                                                                                                                                                      |

!!! info "--not-in-venv"

    The `--not-in-venv`-flag should be used carefully, since workers can automatically install packages in their environment, which is why it creates a new one by default.

    But the --not-in-venv command commes especially handy during the development of new node packages which should be tested within a worker while it is only locally available.

    This behaviour is also used by the `--funcnodes-module demoworker` command.

##### start worker { #worker_start}

To start an existing worker via the cli simlpy run

```bash
funcnodes [common_options] worker --uuid|--name start
```

This will continously run the respective worker until stopped.
!!! important "A Worker can only run one instance at a time"

    The workers are running their node based programm continously. Since they have a fixed state at a given time it is not possible to run a single worker on the same machine (to be more exact with the same base folder) multiple times in paralell. As such if you try to run a worker at it is already running it will automatically stop imediatly.

    If you want to start a worker and it is not working because it says it is already running, you can either try stopping it with the [stop worker][worker_stop] command, or go into the worker directory `<funcnodes directory>/worker` and check for the `worker_<uuid>.p` file. This file contains the pid for the Worker  which can be used to kill it, or you can try to delet the file.<br>
    Note: If the file is deleted, but the worker is still running, it will be recreated.

##### stop worker { #worker_stop}

To stop a running worker via the cli simlpy run

```bash
funcnodes [common_options] worker --uuid|--name stop
```

##### list all worker { #worker_list}

To get a list of all workers the `list` worker task can be utilized:

```bash
funcnodes [common_options] worker list [--full]
```

e.g.

```bash
>> funcnodes worker list
15e84e74d25446cdafc9339e8a437e73        myworker
0a60b90c55e24a448b6714fce3d08aed        test
c52079f077f94929908bbc9013941a08        dummy
```

Without the `--full` option this command will print a list of all existing workers in the form of:

```bash
<uuid>\t<name>
```

if the `--full` option is set the output will print all configuration dictionaries of the existing Workers (see:
[Worker config](../components/worker_config.md)
)

```bash
>> funcnodes worker list --full
[{'data_path': '~/.funcnodes/workers/worker_myworker',
  'env_path': '~/.funcnodes/workers/worker_myworker/.venv',
  'host': 'localhost',
  'name': 'myworker',
  'package_dependencies': {},
  'pid': 39692,
  'port': 9382,
  'python_path': '~/.funcnodes/workers/worker_myworker/.venv/Scripts/python.exe',
  'ssl': False,
  'type': 'WSWorker',
  'update_on_startup': {'funcnodes': True},
  'uuid': 'myworker',
  'worker_dependencies': {}},
 {'data_path': '~/.funcnodes/workers/worker_0a60b90c55e24a448b6714fce3d08aed',
  'env_path': '~/.funcnodes/workers/worker_0a60b90c55e24a448b6714fce3d08aed/.venv',
  'host': 'localhost',
  'name': 'test',
  'package_dependencies': {'funcnodes-basic': {'package': 'funcnodes-basic',
                                               'version': '>=0.2.1'},
                           'funcnodes-files': {'package': 'funcnodes-files',
                                               'version': '0.2.7'},
                           'funcnodes-images': {'package': 'funcnodes-images',
                                                'version': '0.2.2'},
                           'funcnodes-numpy': {'package': 'funcnodes-numpy',
                                               'version': '0.2.9'},
                           'funcnodes-opencv': {'package': 'funcnodes-opencv',
                                                'version': '0.2.2'},
                           'funcnodes-storage': {'package': 'funcnodes-storage',
                                                 'version': '0.1.0'}},
  'pid': 31112,
  'port': 9383,
  'python_path': '~/.funcnodes/workers/worker_0a60b90c55e24a448b6714fce3d08aed/.venv/Scripts/python.exe',
  'ssl': False,
  'type': 'WSWorker',
  'update_on_startup': {'funcnodes': True},
  'uuid': '0a60b90c55e24a448b6714fce3d08aed',
  'worker_dependencies': {}},
 {'data_path': '~/.funcnodes/workers/worker_15e84e74d25446cdafc9339e8a437e73',
  'env_path': '~/.funcnodes/workers/worker_15e84e74d25446cdafc9339e8a437e73/.venv',
  'host': 'localhost',
  'name': 'dummy2',
  'package_dependencies': {'funcnodes-files': {'package': 'funcnodes-files',
                                               'version': '0.2.7'},
                           'funcnodes-opencv': {'package': 'funcnodes-opencv',
                                                'version': '0.2.2'}},
  'pid': 18300,
  'port': 9383,
  'python_path': '~/.funcnodes/workers/worker_15e84e74d25446cdafc9339e8a437e73/.venv/Scripts/python.exe',
  'ssl': False,
  'type': 'WSWorker',
  'update_on_startup': {'funcnodes': True},
  'uuid': '15e84e74d25446cdafc9339e8a437e73',
  'worker_dependencies': {}},
 {'data_path': '~/.funcnodes/workers/worker_c52079f077f94929908bbc9013941a08',
  'env_path': '~/.funcnodes/workers/worker_c52079f077f94929908bbc9013941a08/.venv',
  'host': 'localhost',
  'name': 'dummy',
  'package_dependencies': {'funcnodes-basic': {'package': 'funcnodes-basic',
                                               'version': None},
                           'funcnodes-files': {'package': 'funcnodes-files',
                                               'version': None},
                           'funcnodes-hplc': {'package': 'funcnodes-hplc',
                                              'version': None},
                           'funcnodes-opencv': {'package': 'funcnodes-opencv',
                                                'version': '0.2.2'},
                           'funcnodes-pandas': {'package': 'funcnodes-pandas',
                                                'version': None},
                           'funcnodes-plotly': {'package': 'funcnodes-plotly',
                                                'version': None}},
  'pid': 10568,
  'port': 9382,
  'python_path': '~/.funcnodes/workers/worker_c52079f077f94929908bbc9013941a08/.venv/Scripts/python.exe',
  'ssl': False,
  'type': 'WSWorker',
  'update_on_startup': {'funcnodes': True},
  'uuid': 'c52079f077f94929908bbc9013941a08',
  'worker_dependencies': {}}]

```

##### listen to a worker { #worker_listen}

The CLI provides the option to listen to a worker. It basically continously prints the log of the worker to the current output until the command is terminated. It always prints the current full log data of the worker, so it will also work with workers that are not running, in which case it will simply print the histroical logs, without any new output until the worker starts.

```bash
funcnodes [common_options] worker --uuid|--name listen
```

e.g.

```bash
>> funcnodes worker --name dummy listen
2025-01-30 13:30:03,491 - funcnodes.c52079f077f94929908bbc9013941a08 - INFO - Starting worker forever
2025-01-30 13:30:09,273 - funcnodes.c52079f077f94929908bbc9013941a08 - INFO - Setup loop manager to run
2025-01-30 13:30:09,273 - funcnodes.c52079f077f94929908bbc9013941a08 - INFO - Starting loop manager
2025-01-30 13:30:09,392 - funcnodes.c52079f077f94929908bbc9013941a08 - INFO - WebSocket server running on localhost:9382
```

##### worker modules {#worker_modules}

This command allows to run the [funcnodes module][modules] command within the worker environment

e.g.

```bash
funcnodes [common_options] worker --uuid|--name modules list
```

##### activate worker { #worker_activate}

By default each worker has its own virtual environment to make the installed modules independed for each worker.

```bash
funcnodes [common_options] worker --uuid|--name activate
```

gives a convinient way of directly entering the virtual environment (mainly for debugging purposes or if a package has to be installed manually via the terminal)

e.g.

```bash
>> funcnodes worker --name dummy activate
(worker_c52079f077f94929908bbc9013941a08)>>█
```

##### run py in worker { #worker_py}

```bash
>> funcnodes  worker --uuid|--name py [python_args]
```

This worker task is short for

```bash
>> funcnodes  worker --uuid|--name activate
(env)>> python [python_args]
```

and can be used to directly execute python scripts or task with the python interpreter of the worker

e.g.

```bash
>> funcnodes worker --name dummy py -- -c "print(\"hello\")" # (1)!
hello
>> funcnodes worker --name dummy py -- --version
```

1. If arguments have to be passed to the python directly command they must be seperated via -- from the main command and string quotations need to be properly escaped.

or:
with a local srypt `myscript.py`

```py
# myscript.py
import sys
print(sys.argv)
```

```bash
>> funcnodes worker --name dummy py myscript.py  --innerarg
['myscript.py', '--innerarg']
```

#### workermanager { #workermanager}

To start a [Workermanager](../components/workermanager.md) via the cli you can run

```bash
funcnodes [common_options] startworkermanager [workermanager_options]
```

The optional arguments for this command are:

| Argument | Description                                                                                                                    |
| -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| --host   | The host of the Workermanager, defaults to the [config](../components/config.md)["worker_manager"]["host"] (default:localhost) |
| --port   | The port of the Workermanager, defaults to the [config](../components/config.md)["worker_manager"]["port"] (default:9380)      |

#### modules { #modules}

Funcnodes has a way of automatically detecting available Nodes in the current environment.

The nodes have to be packed in a common [NodeModule](../modules/index.md).

To list all Modules in the current environment run:

```bash
funcnodes [common_options] modules list
```

the output will be an indent list of the installed funcnodes modules:
in the form of:

```bash
funcnodes_basic:
        InstalledModule(name=funcnodes_basic, description=Basic functionalities for
                funcnodes, entry_points=['module', 'shelf'], version=0.2.1, react_plugin=False,
                render_options=False)
```
