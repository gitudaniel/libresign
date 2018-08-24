
from cloudstorage import get_driver_by_name
from cloudstorage.drivers.google import GoogleStorageDriver
from . import config

def container():
    storage = GoogleStorageDriver()
    return storage.get_container(config.STORAGE_CONTAINER)

storage = GoogleStorageDriver()
documents = storage.get_container(config.STORAGE_CONTAINER)
signatures = storage.get_container(config.STORAGE_CONTAINER)

