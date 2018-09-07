import sys
import importlib
import asyncio
import click

from arbiter import listen_and_arbitrate

@click.command()
@click.option('--backend', default='verbatim',
        help='Which backend to use when scanning files.')
@click.option('--test', is_flag=True, default=False,
        help='Exit on errors or successful settle.')
def main(backend, test):

    loaded_backend = importlib.import_module("backends.{0}".format(backend))
    asyncio.get_event_loop().run_until_complete(listen_and_arbitrate(test, loaded_backend))

if __name__ == "__main__":
    main()
