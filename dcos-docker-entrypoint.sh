#!/bin/bash

# See link below for details:
# https://docs.mongodb.com/manual/tutorial/deploy-replica-set-with-keyfile-access-control/

run_cli_command() {
  command_name=$1
  error_msg=$2

  if ! python3 ./cli/mongo_cli.py "$command_name"
  then
    echo "$error_msg"
    mongod --dbpath "${MONGO_DB_PATH}" --shutdown
    exit 1
  fi
}

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
run_cli_command "initiate-replica-set" "Failed to initate replica set."

echo "Creating user administrator..."
run_cli_command "create-user-administrator" "Failed to create user administrator."

echo "Creating cluster administrator..."
run_cli_command "create-cluster-administrator" "Failed to create cluster administrator."

echo "Creating backup user..."
run_cli_command "create-backup-user" "Failed to create backup user."

echo "Creating cluster monitor user..."
run_cli_command "create-cluster-monitor-user" "Failed to create cluster monitor user."

echo "Adding replica to replica set..."
run_cli_command "add-replica-to-replica-set" "Failed to add replica to replica set."

echo "Done"
tail -F "${MONGO_LOG_PATH}"
