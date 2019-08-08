from enum import Enum


class MongoErrorCodes(Enum):
    """
    See https://raw.githubusercontent.com/mongodb/mongo/master/src/mongo/base/error_codes.err
    """
    ALREADY_INITIALIZED = 23,
    DUPLICATE_KEY = 11000
