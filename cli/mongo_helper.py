from collections import OrderedDict
import json
import logging
import os
import time

import jwt
from pymongo import MongoClient
from pymongo.errors import PyMongoError, OperationFailure
import requests

from mongo_error_codes import MongoErrorCodes


class MongoHelper:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())

        # Environment variables provided by marathon.
        self.marathon_app_id = os.getenv("MARATHON_APP_ID")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT0", "27017"))

        # Environment variables specific to this app.
        self.marathon_api_url = os.getenv("MARATHON_API_URL", "http://leader.mesos:8080")
        self.service_account_credentials = os.getenv("DCOS_SERVICE_ACCOUNT_CREDENTIAL")
        self.replica_set = os.getenv("MONGO_REPLICA_SET", "rs")
        self.user_admin_username = os.getenv("MONGO_USER_ADMIN_USERNAME", "user_admin")
        self.user_admin_password = os.getenv("MONGO_USER_ADMIN_PASSWORD", "user_admin")
        self.cluster_admin_username = os.getenv("MONGO_CLUSTER_ADMIN_USERNAME", "cluster_admin")
        self.cluster_admin_password = os.getenv("MONGO_CLUSTER_ADMIN_PASSWORD", "cluster_admin")
        self.backup_username = os.getenv("MONGO_BACKUP_USERNAME", "backup_user")
        self.backup_password = os.getenv("MONGO_BACKUP_PASSWORD", "backup_user")
        self.cluster_monitor_username = os.getenv("MONGO_CLUSTER_MONITOR_USERNAME", "cluster_monitor_user")
        self.cluster_monitor_password = os.getenv("MONGO_CLUSTER_MONITOR_PASSWORD", "cluster_monitor_user")

    # Initiate replica set.
    ####################################################################################################################
    def initiate_replica_set(self):
        return self._try_func(self._initiate_replica_set, max_attempts=20)

    def _initiate_replica_set(self):
        if self._replica_set_initiated():
            self.logger.info("Replica set initiated.")
            return True

        # The first replica initiate the replica set and the others wait.
        if not self._is_first_replica():
            self.logger.info("Waiting for replica set to be initiated...")
            return False

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

        return result and (result.get("ok") or result.get("code") == MongoErrorCodes.ALREADY_INITIALIZED)

    def _replica_set_initiated(self):
        repl_set_get_status = OrderedDict({"replSetGetStatus": 1})

        result = self._run_mongo_command(repl_set_get_status,
                                         local=False,
                                         username=self.cluster_admin_username,
                                         password=self.cluster_admin_password)

        return result and result.get("ok")

    # Create user administrator.
    ####################################################################################################################
    def create_user_administrator(self):
        return self._try_func(self._create_user_administrator)

    def _create_user_administrator(self):
        is_first_replica = self._is_first_replica()
        user_info_result = self._get_user_info(self.user_admin_username, is_first_replica)

        if user_info_result and user_info_result.get("ok") and user_info_result.get("users"):
            self.logger.info("User administrator created.")
            return True

        if not is_first_replica:
            self.logger.info("Waiting for user administrator to be created...")
            return False

        self.logger.info("Creating user administrator...")
        return self._create_user(self.user_admin_username, self.user_admin_password, "userAdminAnyDatabase")

    # Create cluster administrator.
    ####################################################################################################################
    def create_cluster_administrator(self):
        return self._try_func(self._create_cluster_administrator)

    def _create_cluster_administrator(self):
        is_master = self._is_master()
        user_info_result = self._get_user_info(self.cluster_admin_username, is_master)

        if user_info_result and user_info_result.get("ok") and user_info_result.get("users"):
            self.logger.info("Cluster administrator created.")
            return True

        if not is_master:
            self.logger.info("Waiting for cluster administrator to be created...")
            return False

        self.logger.info("Creating cluster administrator...")
        return self._create_user(self.cluster_admin_username, self.cluster_admin_password, "clusterAdmin")

    # Create backup user.
    ####################################################################################################################
    def create_backup_user(self):
        return self._try_func(self._create_backup_user)

    def _create_backup_user(self):
        is_master = self._is_master()
        user_info_result = self._get_user_info(self.backup_username, is_master)

        if user_info_result and user_info_result.get("ok") and user_info_result.get("users"):
            self.logger.info("Backup user created.")
            return True

        if not is_master:
            self.logger.info("Waiting for backup user to be created...")
            return False

        self.logger.info("Creating backup user...")
        return self._create_user(self.backup_username, self.backup_password, "backup")

    # Create cluster monitor user.
    ####################################################################################################################
    def create_cluster_monitor_user(self):
        return self._try_func(self._create_cluster_monitor_user)

    def _create_cluster_monitor_user(self):
        is_master = self._is_master()
        user_info_result = self._get_user_info(self.cluster_monitor_username, is_master)

        if user_info_result and user_info_result.get("ok") and user_info_result.get("users"):
            self.logger.info("Cluster monitor created.")
            return True

        if not is_master:
            self.logger.info("Waiting for cluster monitor user to be created...")
            return False

        self.logger.info("Creating cluster monitor user...")
        return self._create_user(self.cluster_monitor_username, self.cluster_monitor_password, "clusterMonitor")

    # Add replica to replica set.
    ####################################################################################################################
    def add_replica_to_replica_set(self):
        self.logger.info("Updating replica set config...")
        return self._try_func(self._add_replica_to_replica_set)

    def _add_replica_to_replica_set(self):
        rs_config = self._get_current_replica_set_config()

        if not rs_config or not rs_config.get("ok"):
            return False

        # Check if current replica is a member of the replica set.
        for member in rs_config["config"]["members"]:
            if member["host"] == self._get_current_replica_endpoint():
                self.logger.info("Replica is already a member of the replica set...")
                return True

        # If not a member, update replica set config.
        repl_set_reconfig = OrderedDict()
        repl_set_reconfig["replSetReconfig"] = self._get_new_replica_set_config(rs_config)
        repl_set_reconfig["force"] = False

        result = self._run_mongo_command(repl_set_reconfig,
                                         local=False,
                                         username=self.cluster_admin_username,
                                         password=self.cluster_admin_password)

        return result and result.get("ok")

    # Helper functions.
    ####################################################################################################################

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

            result = mongo.admin.command(command)
            self.logger.info(result)
        except OperationFailure as e:
            self.logger.error("{}: {}".format(e.code, e.details))
            result = e.details
        except PyMongoError as e:
            self.logger.exception(e)
        finally:
            if mongo:
                mongo.close()

        return result

    def _get_user_info(self, username, local):
        users_info = OrderedDict({"usersInfo": username})

        return self._run_mongo_command(users_info,
                                       local=local,
                                       username=self.user_admin_username,
                                       password=self.user_admin_password)

    def _create_user(self, username, password, role):
        create_user = OrderedDict()
        create_user["createUser"] = username
        create_user["pwd"] = password
        create_user["roles"] = [{"role": role, "db": "admin"}]

        cmd_usr = None if username == self.user_admin_username else self.user_admin_username
        cmd_pwd = None if username == self.user_admin_username else self.user_admin_password

        result = self._run_mongo_command(create_user, local=True, username=cmd_usr, password=cmd_pwd)

        return result and (result.get("ok") or result.get("code" == MongoErrorCodes.DUPLICATE_KEY))

    def _is_master(self):
        is_master = OrderedDict({"isMaster": 1})

        result = self._run_mongo_command(is_master,
                                         local=True,
                                         username=self.user_admin_username,
                                         password=self.user_admin_password)

        return result and result.get("ok") and result.get("ismaster")

    def _is_first_replica(self):
        return self._get_all_replica_endpoints()[0] == self._get_current_replica_endpoint()

    def _get_current_replica_endpoint(self):
        return "{}:{}".format(self.host, self.port)

    def _get_all_replica_endpoints(self):
        auth_token = self._generate_auth_token()

        resp = requests.get("{}/v2/apps/{}".format(self.marathon_api_url, self.marathon_app_id.strip("/")),
                            headers={"Authorization": "token={}".format(auth_token)})
        if resp.status_code != 200:
            raise Exception("An error occured while calling marathon api:\n{}: {}".format(resp.status_code, resp.text))

        mongo_replicas = []

        json_resp = resp.json()
        if "app" in json_resp and "tasks" in json_resp["app"]:
            for task in resp.json()["app"]["tasks"]:
                for port in task["ports"]:
                    mongo_replicas.append("{}:{}".format(task["host"], port))

        return mongo_replicas

    def _generate_auth_token(self):
        try:
            if not self.service_account_credentials:
                return None

            credentials = json.loads(self.service_account_credentials)

            if "uid" not in credentials or "private_key" not in credentials or "login_endpoint" not in credentials:
                self.logger.error("Invalid service account credentials.")
                return None

            jwt_token = jwt.encode({"uid": credentials["uid"]}, credentials["private_key"], algorithm="RS256")

            resp = requests.post(credentials["login_endpoint"],
                                 json={"uid": credentials["uid"], "token": jwt_token.decode()},
                                 headers={"Content-Type": "application/json"},
                                 verify=False)
            if resp.status_code != 200:
                self.logger.error("Failed to generate auth token:\n{}: {}".format(resp.status_code, resp.text))
                return None

            return resp.json()["token"]
        except Exception as e:
            self.logger.exception(e)

    def _get_current_replica_set_config(self):
        command = OrderedDict({"replSetGetConfig": 1})
        result = self._run_mongo_command(command,
                                         local=False,
                                         username=self.cluster_admin_username,
                                         password=self.cluster_admin_password)
        return result

    def _get_new_replica_set_config(self, rs_config):
        # Generate new config.
        new_config = {
            "_id": "rs",
            "version": rs_config["config"]["version"] + 1 if rs_config else 1,
            "protocolVersion": 1,
            "members": []
        }

        # Keep active replicas from previous config.
        if rs_config:
            endpoints = self._get_all_replica_endpoints()
            for member in rs_config["config"]["members"]:
                if member["host"] in endpoints:
                    new_config["members"].append(member)

        # Add current replica to members list.
        new_config["members"].append({
            "_id": max([i["_id"] for i in rs_config["config"]["members"]]) + 1 if rs_config else 0,
            "host": self._get_current_replica_endpoint()
        })

        return new_config
