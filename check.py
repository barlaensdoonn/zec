#!/usr/bin/python3
# use zcash-cli in python
# 07/19/17
# updated 07/28/17

import sys
import time
import json
import yaml
import addrs
import check_lew
import subprocess
import logging
import logging.config
from datetime import datetime


def get_now():
    now = datetime.now()
    return now.strftime('%m%d%y%H%M%S')


def get_info():
    test = subprocess.check_output(['zcash-cli', 'getinfo'])
    return json.loads(test.decode(sys.stdout.encoding))


def get_balance():
    taddr = addrs.t_addr
    balance = subprocess.check_output(['zcash-cli', 'z_getbalance', taddr])
    return float(balance.decode(sys.stdout.encoding).strip())


def calculate_lews_cut(pymnt):
    # $$$ paid / cost of GPU / total # GPUs mining to taddr
    lews_percent = 500 / 715 / 2
    lews_cut = pymnt * lews_percent
    lews_cut = round(lews_cut, 8)
    logger.info("lew's cut: {}".format(lews_cut))

    return lews_cut


def send_zec(amnt):
    lew_addr = addrs.lew

    logger.info('sending lew mining reward of {}'.format(amnt))
    sent = subprocess.run(['zcash-cli', 'sendtoaddress', lew_addr, str(amnt), 'lew mining cut', 'lew-jaxx', 'true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if sent.returncode == 0:
        txid = sent.stdout.strip()
        logger.info('sent {} to lew [txid: {}]'.format(amnt, txid))
        return True
    else:
        logger.error('{} not sent!!!'.format(amnt))
        log_nonzero_returncode(sent)
        return False


def pickle_and_copy(pickle_flag):
    pckld_path = check_lew.get_pymnts(pickle_flag=pickle_flag)
    logger.info('pickled total zec paid to lew for external earnings calculations')

    scp = subprocess.run(['scp', pckld_path, addrs.scp_path])

    if scp.returncode == 0:
        logger.info('sent pickle to remote host')
    else:
        logger.error('unable to send pickle to remote host')
        log_nonzero_returncode(scp)


def backup_wallet(now):
    bckp = subprocess.run(['zcash-cli', 'backupwallet', 'zecdmp{}'.format(now)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if bckp.returncode == 0:
        logger.info('wallet backed up as {}'.format(bckp.stdout.strip()))
    else:
        logger.error('unable to backup wallet')
        log_nonzero_returncode(bckp)


def parse_change(new_balance, balance):
    payment = new_balance - balance

    if payment > 0:
        mvmnt = 'increase'
    elif payment < 0:
        mvmnt = 'decrease'

    log_new_balance(new_balance, balance, payment, mvmnt)

    if mvmnt == 'increase':
        lews_cut = calculate_lews_cut(payment)
        pickle_flag = send_zec(lews_cut)

        if pickle_flag:
            pickle_and_copy(pickle_flag)

    elif mvmnt == 'decrease':
        logger.info('balance lowered by action external to this script')


def initialize_logger():
    with open('ignore/zec_log.yaml', 'r') as log_conf:
        log_config = yaml.safe_load(log_conf)

    logging.config.dictConfig(log_config)
    logger = logging.getLogger('zec')
    logger.info('* * * * * * * * * * * * * * * * * * * *')
    logger.info('ZEC logger instantiated')

    return logger


def log_new_balance(nblnc, blnc, pymnt, mvmnt):
    logger.info('balance updated: {}'.format(mvmnt))
    logger.info('old balance: {}'.format(blnc))
    logger.info('new balance: {}'.format(nblnc))
    logger.info('payment amount: {}'.format(pymnt))


def log_nonzero_returncode(process):
    logger.warning('subprocess return code: {}'.format(process.returncode))
    logger.warning('subprocess stderr: {}'.format(process.stderr))
    logger.warning('subprocess object: {}'.format(process))


if __name__ == '__main__':
    logger = initialize_logger()
    polling = True
    balance = get_balance()
    new_balance = balance
    logger.info('initial balance: {}'.format(balance))

    try:
        while polling:
            if int(datetime.now().timestamp() % 60) == 0:
                new_balance = get_balance()

                if new_balance != balance:
                    parse_change(new_balance, balance)
                    backup_wallet(get_now())
                    balance = new_balance

                time.sleep(1)

    except KeyboardInterrupt:
        logger.info('...user exit received...')
