#!/usr/bin/python3
# use zcash-cli in python
# 07/19/17
# updated 07/27/17

#TODO: when balance is updated, backup wallet

import sys
import time
import json
import yaml
import addrs
import subprocess
import logging
import logging.config
from datetime import datetime

# $$$ paid / cost of GPU / total # GPUs mining to taddr
louies_cut = 400/730/2
louie_addr = addrs.louie
taddr = addrs.t_addr


def get_info():
    test = subprocess.check_output(['zcash-cli', 'getinfo'])
    return json.loads(test.decode(sys.stdout.encoding))


def get_balance(addr):
    balance = subprocess.check_output(['zcash-cli', 'z_getbalance', addr])
    return float(balance.decode(sys.stdout.encoding).strip())


def get_now():
    now = datetime.now()
    return now.strftime('%m/%d/%y %H:%M:%S')


def initialize_logger():
    with open('ignore/pay_log.yaml', 'r') as log_conf:
        log_config = yaml.safe_load(log_conf)

    logging.config.dictConfig(log_config)
    logger = logging.getLogger('pay')
    logger.info('* * * * * * * * * * * * * * * * * * * *')
    logger.info('ZEC payment logger instantiated')

    return logger


if __name__ == '__main__':
    logger = initialize_logger()
    polling = True
    balance = get_balance(taddr)
    new_balance = balance
    logger.info('initial balance: {}'.format(balance))

    try:
        while polling:
            if int(datetime.now().timestamp() % 60) == 0:
                new_balance = get_balance(taddr)

                if new_balance != balance:
                    payment = new_balance - balance
                    louie_pay = payment * louies_cut
                    logger.info('balance updated')
                    logger.info('old balance: {}'.format(balance))
                    logger.info('new balance: {}'.format(new_balance))
                    logger.info('payment amount: {}'.format(payment))
                    logger.info("louie's cut: {}".format(louie_pay))
                    balance = new_balance
                    time.sleep(1)
                else:
                    time.sleep(1)

    except KeyboardInterrupt:
        logger.info('...user exit received...')
