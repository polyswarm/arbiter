import sys
import argparse
import importlib
import asyncio

from arbiter import listen_and_arbitrate

def main():
    parser = argparse.ArgumentParser(description="Run an arbiter backend.")

    parser.add_argument("--backend", help="Select the backend", default="verbatim")
    parser.add_argument("--test", help="Exits on successful settle", action="store_true")
    args = parser.parse_args()

    backend = importlib.import_module("backends.{0}".format(args.backend))
    loop = asyncio.get_event_loop()
    loop.create_task(listen_and_arbitrate(args.test, backend))
    loop.run_forever()

if __name__ == "__main__":
    main()
