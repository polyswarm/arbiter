import click
import importlib
import logging
import sys

from arbiter.verbatim import VerbatimArbiter

def choose_backend(backend):
    """Resolves arbiter name string to implementation

    Args:
        backend (str): Name of the backend to load, either one of the predefined
            implementations or the name of a module to load
            (module:ClassName syntax or default of module:Arbiter)
    Returns:
        (Class): Arbiter class of the selected implementation
    Raises:
        (Exception): If backend is not found
    """
    arbiter_class = None
    if backend == 'verbatim':
        arbiter_class = VerbatimArbiter
    else:
        import_l = backend.split(":")
        arbiter_module_s = import_l[0]

        arbiter_module = importlib.import_module(arbiter_module_s)
        arbiter_class = arbiter_module.Arbiter if ":" not in backend else getattr(arbiter_module, import_l[1])

    if arbiter_class is None:
        raise Exception("No arbiter backend found {0}".format(backend))

    return arbiter_class


@click.command()
@click.option('--log', default='INFO',
        help='Logging level')
@click.option('--polyswarmd-addr', envvar='POLYSWARMD_ADDR', default='localhost:31337',
        help='Address (host:port) of polyswarmd instance')
@click.option('--keyfile', envvar='KEYFILE', type=click.Path(exists=True), default='keyfile',
        help='Keystore file containing the private key to use with this arbiter')
@click.option('--password', envvar='PASSWORD', prompt=True, hide_input=True,
        help='Password to decrypt the keyfile with')
@click.option('--api-key', envvar='API_KEY', default='',
        help='API key to use with polyswarmd')
@click.option('--backend', envvar='BACKEND', default='scratch',
        help='Backend to use')
@click.option('--testing', default=0,
        help='Activate testing mode for integration testing, respond to N bounties then exit')
@click.option('--insecure-transport', is_flag=True,
        help='Connect to polyswarmd via http:// and ws://, mutially exclusive with --api-key')
def main(log, polyswarmd_addr, keyfile, password, api_key, backend, testing, insecure_transport):
    """Entrypoint for the arbiter driver

    Args:
        polyswarmd_addr(str): Address of polyswarmd
        keyfile (str): Path to private key file to use to sign transactions
        password (str): Password to decrypt the encrypted private key
        backend (str): Backend implementation to use
        api_key(str): API key to use with polyswarmd
        testing (int): Mode to process N bounties then exit (optional)
        insecure_transport (bool): Connect to polyswarmd without TLS
    """

    loglevel = getattr(logging, log.upper(), None)
    if not isinstance(loglevel, int):
        logging.error('invalid log level')
        sys.exit(-1)
    logging.basicConfig(level=loglevel)

    arbiter_class = choose_backend(backend)
    arbiter_class(polyswarmd_addr, keyfile, password, api_key, testing, insecure_transport).run()


if __name__ == "__main__":
    main()
