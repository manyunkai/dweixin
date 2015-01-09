# -*-coding:utf-8 -*-
"""
Created on 2015-01-06

@author: Danny
DannyWork Project
"""

from django.dispatch import Signal


event_adder = Signal(providing_args=['type', 'pool', 'ident', 'belonging', 'from_user', 'user_message', 'reply',
                                     'processed_status', 'processed_message'])