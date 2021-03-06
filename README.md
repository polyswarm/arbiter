# SECURITY WARNING

`arbiter` implicitly trusts transaction signing requests from `polyswarmd`.
A malicious instance of `polyswarmd` or an attacker with sufficient network capabilities may abuse this trust relationship to cause `arbiter` to transfer all NCT, ETH or other tokens to an attacker address.

Therefore:
1. **ONLY CONNECT `arbiter` TO `polyswarmd` INSTANCES THAT YOU TRUST**
2. **DO NOT ALLOW `arbiter` <-> `polyswarmd` COMMUNICATIONS TO TRAVERSE AN UNTRUSTED NETWORK LINK**

In other words, only run `arbiter` on a co-located `localhost` with `polyswarmd`.

This is a temporarily limitation - `arbiter`'s trust in `polyswarmd` will be eliminated in the near future.

# Arbiter

This project hosts a means to run an arbiter easily.

## Run an Arbiter

`arbiter --backends <name of backend module>`

The default backend is `verbatim` if no backend is set.

## Adding an arbiter backend

All backends must be their own python module inside the `backends/` directory. The name of the file will be the name used to load the backend.

At a minimum, it must have a `scan(host, uri)` function that returns an array of boolean verdicts.

## Generate verbatim database

The verbatim scanner uses a database called `truth.db`
The arbiter projects includes a helper to generate that database.
Run the command with `generate_verbatim`.
By default that will load benign files from `artifacts/benign` and malicious files from `artifacts/malicious`.
The output database is `artifacts/truth.db`.

```bash
$ generate_verbatim --help
Usage: generate_verbatim [OPTIONS]

Options:
  --malicious PATH  Input directory of malicious files
  --benign PATH     Input directory of benign files
  --output PATH     Output database file.
  --help            Show this message and exit.
```

The created database is a single table called `files`.
The table has two columns, `(name text, truth int)`.

## Error codes

There are three major events that cause errors

* **11** Arbiter backend failed to return any verdicts (Including an empty list)
* **12** Arbiter failed to vote. (Check that the given address is added as an arbiter & staked )
* **13** Arbiter failed to settle the bounty. (Check that the given address is added as an arbiter & staked )