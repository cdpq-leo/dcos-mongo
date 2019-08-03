# Mongo for DC/OS

### Build docker image
```
docker build -t cdpqleo/mongodb:4.0.10 .
```

### Deploy on DC/OS
```
dcos marathon app install ./marathon/mongo.json
```

### Supported environment variables
- MONGO_SSL_KEY
- MONGO_REPLICA_SET
- MONGO_DB_PATH
- MONGO_LOG_PATH
- MONGO_USER_ADMIN_USERNAME
- MONGO_USER_ADMIN_PASSWORD
- MONGO_CLUSTER_ADMIN_USERNAME
- MONGO_CLUSTER_ADMIN_PASSWORD
- MESOS_URL
- LOG_LEVEL

### Generate SSL key
```
openssl rand -base64 756
```
