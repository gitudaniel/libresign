
import logging

# You can't install cloudstorage successfully on
# windows, disable the warning
# pylint: disable=E0401
from cloudstorage.exceptions import NotFoundError

from .. import storage, app
from ..helpers import type_check

@app.celery.task
@type_check
def delete_blobs(names: list):
    ''' Delete a list of file blobs, it will continue
        the deletion even if some of the blobs don't
        exist. Note that this means that a periodic
        cleanup must be done to catch files that this
        task fails to delete. (e.g. if the task creating
        them is still running)

        Arguments:
            names (list): A list of blob names (as used in the storage container) to delete.
    '''

    print("Starting delete task!")
    container = storage.container()

    for name in names:
        if not isinstance(name, str):
            logging.error(
                'expected name to be an instance of str, found %s instead.',
                str(type(name))
            )
            continue
        
        try:
            blob = container.get_blob(name)
            blob.delete()
        except NotFoundError:
            logging.error(
                "Failed to delete blob %s",
                str(name)
            )
