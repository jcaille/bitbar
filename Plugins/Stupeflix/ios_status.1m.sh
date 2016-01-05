#!/bin/sh
source ~/bundle/set_env
senv;
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH="$DIR:$PYTHONPATH"
python -c "from helpers.helper import print_platform_status as print_platform_status ; print_platform_status('ios')"