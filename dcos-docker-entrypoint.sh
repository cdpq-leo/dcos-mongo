#!/bin/bash

# See link below for details:
# https://docs.mongodb.com/manual/tutorial/deploy-replica-set-with-keyfile-access-control/

if [[ -z "$MARATHON_APP_ID" ]];
then
  echo "Not a marathon app."
  exit 1
fi

echo "Creating keyfile..."
mkdir -p /etc/ssl
echo "${MONGO_SSL_KEY}" >> /etc/ssl/mongo.key
chmod 400 /etc/ssl/mongo.key

echo "Starting replica..."
mongod \
  --bind_ip 0.0.0.0 \
  --replSet "${MONGO_REPLICA_SET:-rs}" \
  --dbpath "${MONGO_DB_PATH:-/data/db}" \
  --logpath "${MONGO_LOG_PATH:-/var/log/mongodb/mongod.log}" \
  --auth \
  --clusterAuthMode keyFile \
  --keyFile /etc/ssl/mongo.key \
  --setParameter authenticationMechanisms=SCRAM-SHA-1 \
  &

echo "Initiating replica set..."
if ! python3 /usr/local/bin/cli/mongo_cli.py initiate-replica-set
then
  echo "Failed to initate replica set."
  mongod --dbpath "${MONGO_DB_PATH:-/data/db}" --shutdown
  exit 1
fi

echo "Creating user administrator..."
if ! python3 /usr/local/bin/cli/mongo_cli.py create-user-administrator
then
  echo "Failed to create user administrator."
  mongod --dbpath "${MONGO_DB_PATH:-/data/db}" --shutdown
  exit 1
fi

echo "Creating cluster administrator..."
if ! python3 /usr/local/bin/cli/mongo_cli.py create-cluster-administrator
then
  echo "Failed to create cluster administrator."
  mongod --dbpath "${MONGO_DB_PATH:-/data/db}" --shutdown
  exit 1
fi

echo "Adding replica to replica set..."
if ! python3 /usr/local/bin/cli/mongo_cli.py add-replica-to-replica-set
then
  echo "Failed to add replica to replica set."
  mongod --dbpath "${MONGO_DB_PATH:-/data/db}" --shutdown
  exit 1
fi

echo "Done"
tail -F "${MONGO_LOG_PATH:-/var/log/mongodb/mongod.log}"
