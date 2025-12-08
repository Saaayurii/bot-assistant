from utils.queued_logger import QueuedLogger

# Base App Exception 

class BaseAppException(Exception):
    logger = QueuedLogger()

    def __init__(self, msg):
        self.logger.error(msg, self)
        super().__init__(self, msg)

# Utils' Exceptions

class BaseUtilsException(BaseAppException):
    pass

class MissingLocalStorageVariable(BaseUtilsException):
    pass

class FailedToOpenLocalStorage(BaseUtilsException):
    pass

class FailedToSerializeLocalStorage(BaseUtilsException):
    pass

class EmptyLocalStorage(BaseUtilsException):
    pass

# Vllm Exceptions

class BaseVllmException(BaseAppException):
    pass

class MissingModelPathException(BaseVllmException):
    pass

class VllmFailedAllRetriesException(BaseVllmException):
    pass
