# Mongo for DC/OS

### Supported environment variables

**MONGO_SSL_KEY**  
SSL key that replicas are using to communicate with each other.  
Can be generated with the following command:
```
openssl rand -base64 756
```

**MONGO_REPLICA_SET**  
Replica set name.  
See https://docs.mongodb.com/manual/reference/program/mongod/#cmdoption-mongod-replset

**MONGO_DB_PATH**  
The directory where the mongod instance stores its data.  
See https://docs.mongodb.com/manual/reference/program/mongod/#cmdoption-mongod-dbpath

**MONGO_LOG_PATH**  
Log file path.  
See https://docs.mongodb.com/manual/reference/program/mongod/#cmdoption-mongod-logpath

**MONGO_USER_ADMIN_USERNAME**  
Username of the userAdmin user.  
See https://docs.mongodb.com/manual/reference/built-in-roles/#userAdmin
  
**MONGO_USER_ADMIN_PASSWORD**  
Password of the userAdmin user.  
See https://docs.mongodb.com/manual/reference/built-in-roles/#userAdmin
 
**MONGO_CLUSTER_ADMIN_USERNAME**  
Username of the clusterAdmin user.  
See https://docs.mongodb.com/manual/reference/built-in-roles/#clusterAdmin

**MONGO_CLUSTER_ADMIN_PASSWORD**  
Password of the clusterAdmin user.  
See https://docs.mongodb.com/manual/reference/built-in-roles/#clusterAdmin

**DCOS_SERVICE_ACCOUNT_CREDENTIAL**  
Service credentials having the following format:
```
{
  "scheme": "RS256",
  "uid": "service-acct",
  "private_key": "<private-key-value>",
  "login_endpoint": "https://leader.mesos/acs/api/v1/auth/login"
}
```

**MARATHON_API_URL**    
Marathon api url used to retrieve the list of replicas.  
See https://docs.d2iq.com/mesosphere/dcos/1.13/deploying-services/marathon-api/

### Build docker image
```
docker build -t cdpqleo/mongodb:4.0.10 .
```

### Deploy on DC/OS
```
dcos marathon app install ./marathon/mongo.json
```
