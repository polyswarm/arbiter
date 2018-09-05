import db
import click

@click.command()
@click.option('--malicious', type=click.Path(exists=True), default='./artifacts/malicious',
        help='Input directory of malicious files')
@click.option('--benign', type=click.Path(exists=True), default='./artifacts/benign',
        help='Input directory of benign files')
@click.option('--output', type=click.Path(), default='./artifacts/truth.db',
        help='Output database file.')
def main(malicious, benign, output):
    db.generate_db(output, malicious, benign)

if __name__ == "__main__":
    main()
