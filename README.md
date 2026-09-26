# pump-gcp-radar

Extra commands for [gcp-radar](https://pypi.org/project/gcp-radar/), added through
its plugin hook (`gcp_radar.commands` entry points, gcp-radar 1.3.0+).

## Install

```bash
pip install pump-gcp-radar
```

## Usage

`pump-gcp-radar` runs the normal gcp-radar CLI with this package's commands added:

```bash
pump-gcp-radar --help                       # built-in and pump commands together
pump-gcp-radar run --project my-proj        # gcp-radar built-in
pump-gcp-radar pump-report --project my-proj  # example command from this package
```

## Adding a command

1. Add a `register(subparsers)` function in `src/pump_gcp_radar/commands.py`
   (add a subparser and `set_defaults(func=handler)`).
2. Register it in `pyproject.toml`:

   ```toml
   [project.entry-points."gcp_radar.commands"]
   my-command = "pump_gcp_radar.commands:register_my_command"
   ```
3. Reinstall (`pip install -e .`) so the entry point is picked up.

Command names can't clash with gcp-radar's built-ins (`inventory`, `commitments`,
`billing`, `diagram`, `run`); clashing plugins are skipped with a warning.

## Development

```bash
pip install -e ".[dev]"
pytest
```
