# -*-coding:utf-8 -*-
"""
Created on 2015-01-11

@author: Danny
DannyWork Project
"""

import threading
import logging
import time

from .handlers import handle_customer_service_msg

logger = logging.getLogger(__name__)


class AsyncEventHandler(threading.Thread):

    def __init__(self, pool, label):
        threading.Thread.__init__(self)
        self.pool = pool
        self.label = label

    def run(self):
        while True:
            loop_name = '[Thread for POOL {0} - {1}]Loop at {2}'.format(self.pool, self.label, time.time())
            try:
                status, message = handle_customer_service_msg(self.pool)
            except Exception, e:
                logger.error(str(e))
            else:
                if status:
                    log = 'Processed succeed in {0}.'.format(loop_name)
                else:
                    log = 'Processor returned with status False in {0}. {1}'.format(loop_name, message)
                logger.info(log)
