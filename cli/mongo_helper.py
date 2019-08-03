from collections import OrderedDict
import logging
import os
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError
import requests


class MongoHelper:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())

        self.mesos_url = os.getenv("MESOS_URL", "http://leader.mesos:8080")
        self.marathon_app_id = os.getenv("MARATHON_APP_ID")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT0", "27017"))
        self.replica_set = os.getenv("MONGO_REPLICA_SET", "rs")
        self.user_admin_username = os.getenv("MONGO_USER_ADMIN_USERNAME", "user_admin")
        self.user_admin_password = os.getenv("MONGO_USER_ADMIN_PASSWORD", "user_admin")
        self.cluster_admin_username = os.getenv("MONGO_CLUSTER_ADMIN_USERNAME", "cluster_admin")
        self.cluster_admin_password = os.getenv("MONGO_CLUSTER_ADMIN_PASSWORD", "cluster_admin")

    # Initiate replica set.
    ####################################################################################################################
    def initiate_replica_set(self):
        return self._try_func(self._initiate_replica_set, max_attempts=18)

    def _initiate_replica_set(self):
        # Make sure we initiate replica set only once.
        if not self._is_first_replica():
            # Other replicas wait for the replica set to be initiated, in case of failure of the first replica
            # before de the replica set is initiated.
            self.logger.info("Waiting for replica set to be initiated...")
            return self._replica_set_initiated()

        # Initiate replica set on first replica.
        self.logger.info("Initiating replica set...")

        repl_set_initiate = OrderedDict({
            "replSetInitiate": {
                "_id": "rs",
                "version": 1,
                "protocolVersion": 1,
                "members": [{"_id": 0, "host": "{}:{}".format(self.host, self.port)}]
            }
        })

        result = self._run_mongo_command(repl_set_initiate, local=True)

        return self._mongo_command_succeeded(result)

    def _replica_set_initiated(self, local=False):
        repl_set_get_status = OrderedDict({"replSetGetStatus": 1})

        result = self._run_mongo_command(repl_set_get_status,
                                         local=local,
                                         username=self.cluster_admin_username,
                                         password=self.cluster_admin_password)

        return self._mongo_command_succeeded(result)

    def _is_first_replica(self):
        return self._get_all_replica_endpoints()[0] == self._get_current_replica_endpoint()

    # Create user administrator.
    ####################################################################################################################
    def create_user_administrator(self):
        return self._try_func(self._create_user_administrator)

    def _create_user_administrator(self):
        if not self._is_first_replica():
            return True

        self.logger.info("Creating user administrator...")

        create_user = OrderedDict()
        create_user["createUser"] = self.user_admin_username
        create_user["pwd"] = self.user_admin_password
        create_user["roles"] = [{"role": "userAdminAnyDatabase", "db": "admin"}]

        result = self._run_mongo_command(create_user, local=True)

        return self._mongo_command_succeeded(result)

    # Create cluster administrator.
    ####################################################################################################################
    def create_cluster_administrator(self):
        return self._try_func(self._create_cluster_administrator)

    def _create_cluster_administrator(self):
        if not self._is_first_replica():
            return True

        create_user = OrderedDict()
        create_user["createUser"] = self.cluster_admin_username
        create_user["pwd"] = self.cluster_admin_password
        create_user["roles"] = [{"role": "clusterAdmin", "db": "admin"}]

        result = self._run_mongo_command(create_user,
                                         local=True,
                                         username=self.user_admin_username,
                                         password=self.user_admin_password)

        return self._mongo_command_succeeded(result)

    # Add replica to replica set.
    ####################################################################################################################
    def add_replica_to_replica_set(self):
        self.logger.info("Updating replica set config...")
        return self._try_func(self._add_replica_to_replica_set)

    def _add_replica_to_replica_set(self):
        repl_set_reconfig = OrderedDict()
        repl_set_reconfig["replSetReconfig"] = self._get_new_replica_set_config()
        repl_set_reconfig["force"] = False

        result = self._run_mongo_command(repl_set_reconfig,
                                         local=False,
                                         username=self.cluster_admin_username,
                                         password=self.cluster_admin_password)

        return self._mongo_command_succeeded(result)

    # Helper functions.
    ####################################################################################################################

    @staticmethod
    def _mongo_command_succeeded(result):
        return result and result.get("ok", 0) == 1

    @staticmethod
    def _try_func(func, max_attempts=6, sleep=10):
        success = False
        num_attempts = 0

        while not success and num_attempts < max_attempts:
            success = func()
            if not success:
                num_attempts += 1
                time.sleep(sleep)

        return success

    def _run_mongo_command(self, command, local, username=None, password=None):
        mongo = None
        result = None

        try:
            host = "0.0.0.0" if local else self._get_all_replica_endpoints()
            replicaset = None if local else self.replica_set

            mongo = MongoClient(host,
                                replicaset=replicaset,
                                username=username,
                                password=password,
                                document_class=OrderedDict)

            self.logger.info("Command: {}".format(command))
            result = mongo.admin.command(command)
            self.logger.info("Result: {}".format(result))
        except PyMongoError as e:
            self.logger.exception(e)
        finally:
            if mongo:
                mongo.close()

        return result

    def _get_current_replica_endpoint(self):
        return "{}:{}".format(self.host, self.port)

    def _get_all_replica_endpoints(self):
        resp = requests.get("{}/v2/apps/{}".format(self.mesos_url, self.marathon_app_id.strip("/")))
        if resp.status_code != 200:
            raise Exception("An error occured while calling marathon api.")

        mongo_replicas = []

        json_resp = resp.json()
        if "app" in json_resp and "tasks" in json_resp["app"]:
            for task in resp.json()["app"]["tasks"]:
                for port in task["ports"]:
                    mongo_replicas.append("{}:{}".format(task["host"], port))

        return mongo_replicas

    def _get_current_replica_set_config(self):
        command = OrderedDict({"replSetGetConfig": 1})
        result = self._run_mongo_command(command,
                                         local=False,
                                         username=self.cluster_admin_username,
                                         password=self.cluster_admin_password)
        return result

    def _get_new_replica_set_config(self):
        current_config = self._get_current_replica_set_config()
        new_config_version = current_config["config"]["version"]+1 if current_config else 1

        # Build config based on marathon app endpoints.
        new_config = {"_id": "rs", "version": new_config_version, "protocolVersion": 1, "members": []}
        for i, host in enumerate(self._get_all_replica_endpoints()):
            new_config["members"].append({"_id": i, "host": host})

        return new_config
