import click
from mongo_helper import MongoHelper


@click.group()
def cli():
    pass


@cli.command()
def initiate_replica_set():
    if not MongoHelper().initiate_replica_set():
        raise Exception("Failed to init replica set.")


@cli.command()
def create_user_administrator():
    if not MongoHelper().create_user_administrator():
        raise Exception("Failed to create user administrator.")


@cli.command()
def create_cluster_administrator():
    if not MongoHelper().create_cluster_administrator():
        raise Exception("Failed to create cluster administrator.")


@cli.command()
def add_replica_to_replica_set():
    if not MongoHelper().add_replica_to_replica_set():
        raise Exception("Failed to add replica to replica set.")


cli.add_command(initiate_replica_set)
cli.add_command(create_user_administrator)
cli.add_command(create_cluster_administrator)
cli.add_command(add_replica_to_replica_set)

if __name__ == '__main__':
    cli()
