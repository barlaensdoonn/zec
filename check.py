#!/usr/bin/python3
# use zcash-cli in python
# 7/19/17
# updated 11/6/17

# TODO: change lews_percent variable in calculate_lews_cut to something that is passed in

import os
import sys
import time
import json
import yaml
import addrs
import shutil
import check_lew
import subprocess
import logging
import logging.config
from datetime import datetime


def _get_dir_path():
    return os.path.dirname(os.path.realpath(__file__))


def _get_pickle_path(pickle_flag):
    logger.info('pickling total zec paid to lew for external earnings calculations')
    return check_lew.get_pymnts(pickle_flag=pickle_flag)


def _copy(src_path, dst):
    thng = src_path.split('/')[-1]
    dst_path = os.path.join(dst, thng)

    return shutil.copy2(src_path, dst_path)


def _scp(local_path, remote_path):
    return subprocess.run(['scp', local_path, remote_path])


def _log_new_balance(nblnc, blnc, pymnt, mvmnt):
    logger.info('balance updated: {}'.format(mvmnt))
    logger.info('old balance: {}'.format(blnc))
    logger.info('new balance: {}'.format(nblnc))
    logger.info('payment amount: {}'.format(pymnt))


def _log_nonzero_returncode(process):
    logger.warning('subprocess return code: {}'.format(process.returncode))
    logger.warning('subprocess stderr: {}'.format(process.stderr))
    logger.warning('subprocess object: {}'.format(process))


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
        _log_nonzero_returncode(sent)
        return False


def backup_wallet(now):
    bckp = subprocess.run(['zcash-cli', 'backupwallet', 'dmp{}'.format(now)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    if bckp.returncode == 0:
        wallet_path = bckp.stdout.strip()
        logger.info('wallet backed up as {}'.format(wallet_path))
        return wallet_path
    else:
        logger.error('unable to backup wallet')
        _log_nonzero_returncode(bckp)
        return None


def copy_wallet(wllt_path):
    if not wllt_path:
        return
    else:
        dst = addrs.local_copy_path

        try:
            cpywllt_path = _copy(wllt_path, dst)

            if os.path.isfile(cpywllt_path):
                logger.info('wallet backup copied to {}'.format(cpywllt_path))
        except Exception as e:
            logger.exception('unable to copy wallet backup to {}, printing traceback:'.format(dst))


def copy_pickle(pickle_flag):
    pckld_path = _get_pickle_path(pickle_flag)
    dst = addrs.local_pickle_path

    try:
        cpypckl_path = _copy(pckld_path, dst)

        if os.path.isfile(pckld_path):
            logger.info('earnings pickle copied to {}'.format(cpypckl_path))
    except Exception as e:
        logger.exception('unable to copy pickle to {}, printing traceback:'.format(dst))


def scp_wallet(wllt_path):
    if not wllt_path:
        return
    else:
        scpwllt = _scp(wllt_path, addrs.scp_wallet_path)

        if scpwllt.returncode == 0:
            logger.info('backed up wallet to remote host')
        else:
            logger.error('unable to backup wallet to remote host')
            _log_nonzero_returncode(scpwllt)


def scp_pickle(pickle_flag):
    pckld_path = _get_pickle_path(pickle_flag)
    scpckl = _scp(pckld_path, addrs.scp_pickle_path)

    if scpckl.returncode == 0:
        logger.info('sent pickle to remote host')
    else:
        logger.error('unable to send pickle to remote host')
        _log_nonzero_returncode(scpckl)


def parse_change(new_balance, balance):
    payment = new_balance - balance

    if payment > 0:
        mvmnt = 'increase'
    elif payment < 0:
        mvmnt = 'decrease'

    _log_new_balance(new_balance, balance, payment, mvmnt)

    if mvmnt == 'increase':
        lews_cut = calculate_lews_cut(payment)
        pickle_flag = send_zec(lews_cut)

        if pickle_flag:
            copy_pickle(pickle_flag)


def initialize_logger():
    conf_path = os.path.join(_get_dir_path(), 'ignore/zec_log.yaml')

    with open(conf_path, 'r') as log_conf:
        log_config = yaml.safe_load(log_conf)

    logging.config.dictConfig(log_config)
    logger = logging.getLogger('zec')
    logger.info('* * * * * * * * * * * * * * * * * * * *')
    logger.info('ZEC logger instantiated')

    return logger


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

    while polling:
        try:
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
            polling = False
