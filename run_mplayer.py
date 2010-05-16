#!/usr/bin/env python

import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import settings
#from django.core.management import setup_environ
from player.mplayer import run_server

#setup_environ(settings)

#os.environ['DJANGO_SETTINGS_MODULE'] = 'dj_ango.settings'

if __name__ == '__main__':
    run_server()