# Arbiter

This project hosts a means to run an arbiter easily.

# Run an Arbiter

`python arbiter.py --backends <name of backend module>`

The default backend is `verbatim` if no backend is set.

# Adding an arbiter backend

All backends must be their own python module inside the `backends/` directory. The name of the file will be the name used to load the backend.

At a minimum, it must have a `scan(uri)` function that returns an array of boolean verdicts.

# Error codes

There are three major events that cause errors

* **11** Arbiter backend failed to return any verdicts (Including an empty list)
* **12** Arbiter failed to vote. (Check that the given address is added as an arbiter & staked )
* **13** Arbiter failed to settle the bounty. (Check that the given address is added as an arbiter & staked )