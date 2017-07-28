#!/usr/bin/python3
# use zcash-cli in python
# 07/19/17
# updated 07/28/17

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
louies_percent = 400 / 715 / 2
louie_addr = addrs.louie
taddr = addrs.t_addr


def get_now():
    now = datetime.now()
    return now.strftime('%m%d%y%H%M%S')


def get_info():
    test = subprocess.check_output(['zcash-cli', 'getinfo'])
    return json.loads(test.decode(sys.stdout.encoding))


def get_balance(addr):
    balance = subprocess.check_output(['zcash-cli', 'z_getbalance', addr])
    return float(balance.decode(sys.stdout.encoding).strip())


def send_zec(amnt):
    return subprocess.run(['zcash-cli', 'sendtoaddress', louie_addr, str(amnt), 'louie mining cut', 'louie-jaxx', 'true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


def backup_wallet(now):
    bckp = subprocess.run(['zcash-cli', 'backupwallet', 'zecdmp{}'.format(now)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if bckp.returncode == 0:
        logger.info('wallet backed up as {}'.format(bckp.stdout.strip()))
    else:
        logger.warning('unable to backup wallet')
        logger.warning('subprocess return code: {}'.format(bckp.returncode))
        logger.warning('subprocess stderr: {}'.format(bckp.stderr))
        logger.warning('subprocess object: {}'.format(bckp))


def parse_change(new_balance, balance):
    payment = new_balance - balance

    if payment > 0:
        mvmnt = 'increase'
    elif payment < 0:
        mvmnt = 'decrease'

    log_new_balance(new_balance, balance, payment, mvmnt)

    if mvmnt == 'increase':
        louies_cut = payment * louies_percent
        logger.info("louie's cut: {}".format(louies_cut))
        logger.info('sending louie mining reward of {}'.format(louies_cut))
        sent = send_zec(louies_cut)

        if sent.returncode == 0:
            txid = sent.stdout.strip()
            logger.info('sent {} to louie [txid: {}]'.format(louies_cut, txid))
        else:
            logger.error('{} not sent!!!')
            logger.error('subprocess return code: {}'.format(sent.returncode))
            logger.error('subprocess stderr: {}'.format(sent.stderr))
            logger.error('subprocess object: {}'.format(sent))
    elif mvmnt == 'decrease':
        logger.info('balance lowered by action external to this script')


def initialize_logger():
    with open('ignore/pay_log.yaml', 'r') as log_conf:
        log_config = yaml.safe_load(log_conf)

    logging.config.dictConfig(log_config)
    logger = logging.getLogger('pay')
    logger.info('* * * * * * * * * * * * * * * * * * * *')
    logger.info('ZEC payment logger instantiated')

    return logger


def log_new_balance(nblnc, blnc, pymnt, mvmnt):
    logger.info('balance updated: {}'.format(mvmnt))
    logger.info('old balance: {}'.format(blnc))
    logger.info('new balance: {}'.format(nblnc))
    logger.info('payment amount: {}'.format(pymnt))


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
                    parse_change(new_balance, balance)
                    backup_wallet(get_now())
                    balance = new_balance

                time.sleep(1)

    except KeyboardInterrupt:
        logger.info('...user exit received...')
