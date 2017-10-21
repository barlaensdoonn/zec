#!/usr/bin/python3
# use zcash-cli in python
# 7/19/17
# updated 10/10/17

# TODO: change lews_percent variable in calculate_lews_cut to something that is passed in?

import os
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


def get_dir_path():
    return os.path.dirname(os.path.realpath(__file__))


def get_now():
    now = datetime.now()
    return now.strftime('%m%d%y%H%M%S')


def scp(local_path, remote_path):
    return subprocess.run(['scp', local_path, remote_path])


def get_info():
    test = subprocess.check_output(['zcash-cli', 'getinfo'])
    return json.loads(test.decode(sys.stdout.encoding))


def get_balance():
    taddr = addrs.t_addr
    balance = subprocess.check_output(['zcash-cli', 'z_getbalance', taddr])
    return float(balance.decode(sys.stdout.encoding).strip())


def calculate_lews_cut(pymnt):
    # $$$ paid / cost of GPU / total # GPUs mining to taddr
    lews_percent = 0.25
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
        logger.info('sent lew {} [txid: {}]'.format(amnt, txid))
        return True
    else:
        logger.error('{} not sent!!!'.format(amnt))
        log_nonzero_returncode(sent)
        return False


def pickle_and_copy(pickle_flag):
    pckld_path = check_lew.get_pymnts(pickle_flag=pickle_flag)
    logger.info('pickling total zec paid to lew for external earnings calculations')

    scpckl = scp(pckld_path, addrs.scp_pickle)

    if scpckl.returncode == 0:
        logger.info('sent pickle to remote host')
    else:
        logger.error('unable to send pickle to remote host')
        log_nonzero_returncode(scpckl)


def backup_wallet(now):
    bckp = subprocess.run(['zcash-cli', 'backupwallet', 'zecdmp{}'.format(now)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if bckp.returncode == 0:
        wallet_path = bckp.stdout.strip()
        logger.info('wallet backed up as {}'.format(wallet_path))
        return wallet_path
    else:
        logger.error('unable to backup wallet')
        log_nonzero_returncode(bckp)
        return None


def copy_wallet(wllt_path):
    if not wllt_path:
        return
    else:
        scpwllt = scp(wllt_path, addrs.scp_wallet)

        if scpwllt.returncode == 0:
            logger.info('backed up wallet to remote host')
        else:
            logger.error('unable to backup wallet to remote host')
            log_nonzero_returncode(scpwllt)


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


def initialize_logger():
    conf_path = os.path.join(get_dir_path(), 'ignore/zec_log.yaml')

    with open(conf_path, 'r') as log_conf:
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

    # wait for system to boot up and zcashd to start
    logger.info('sleeping for 3 mins')
    time.sleep(180)

    polling = True
    balance = get_balance()
    new_balance = balance
    logger.info('initial balance: {}'.format(balance))
    logger.info('<> <> <> <> <> <> <> <> <> <> <> <> <>')

    try:
        while polling:
            if int(datetime.now().timestamp() % 60) == 0:
                new_balance = get_balance()

                if new_balance != balance:
                    parse_change(new_balance, balance)
                    bckd_up = backup_wallet(get_now())
                    copy_wallet(bckd_up)
                    balance = new_balance
                    logger.info('<> <> <> <> <> <> <> <> <> <> <> <> <>')

                time.sleep(1)
    except Exception as e:
        logger.exception('encountered error, printing traceback:')
    except KeyboardInterrupt:
        logger.info('...user exit received...')
