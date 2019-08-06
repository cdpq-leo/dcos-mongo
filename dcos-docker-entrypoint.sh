#!/bin/bash

# See link below for details:
# https://docs.mongodb.com/manual/tutorial/deploy-replica-set-with-keyfile-access-control/

if [[ -z "$MARATHON_APP_ID" ]];
then
  echo "Not a marathon app."
  exit 1
fi

# Default values.
MONGO_REPLICA_SET=${MONGO_REPLICA_SET:-rs}
MONGO_DB_PATH=${MONGO_DB_PATH:-/opt/mongodb/data}
MONGO_LOG_PATH=${MONGO_LOG_PATH:-/opt/mongodb/logs/mongod.log}

echo "Creating keyfile..."
mkdir -p /etc/ssl
echo "${MONGO_SSL_KEY}" >> /etc/ssl/mongo.key
chmod 400 /etc/ssl/mongo.key

echo "Starting replica..."
mongod \
  --bind_ip 0.0.0.0 \
  --replSet "${MONGO_REPLICA_SET}" \
  --dbpath "${MONGO_DB_PATH}" \
  --logpath "${MONGO_LOG_PATH}" \
  --auth \
  --clusterAuthMode keyFile \
  --keyFile /etc/ssl/mongo.key \
  --setParameter authenticationMechanisms=SCRAM-SHA-1 \
  &

echo "Initiating replica set..."
if ! python3 ./cli/mongo_cli.py initiate-replica-set
then
  echo "Failed to initate replica set."
  mongod --dbpath "${MONGO_DB_PATH}" --shutdown
  exit 1
fi

echo "Creating user administrator..."
if ! python3 ./cli/mongo_cli.py create-user-administrator
then
  echo "Failed to create user administrator."
  mongod --dbpath "${MONGO_DB_PATH}" --shutdown
  exit 1
fi

echo "Creating cluster administrator..."
if ! python3 ./cli/mongo_cli.py create-cluster-administrator
then
  echo "Failed to create cluster administrator."
  mongod --dbpath "${MONGO_DB_PATH}" --shutdown
  exit 1
fi

echo "Adding replica to replica set..."
if ! python3 ./cli/mongo_cli.py add-replica-to-replica-set
then
  echo "Failed to add replica to replica set."
  mongod --dbpath "${MONGO_DB_PATH}" --shutdown
  exit 1
fi

echo "Done"
tail -F "${MONGO_LOG_PATH}"
