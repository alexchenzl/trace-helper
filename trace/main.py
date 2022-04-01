# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import json
import argparse
import datetime

from web3 import HTTPProvider, Web3
from trace.tracer.tracer import load_tracer


def trace_tx(provider: HTTPProvider, tx_hash, tracer, timeout=30):
    params = [tx_hash, {
        'disableStack': True,
        'disableMemory': True,
        'disableStorage': True,
        'timeout': str(timeout) + 's',
    }]
    if tracer is not None:
        params[1]['tracer'] = tracer
    return provider.make_request('debug_traceTransaction', params)


def trace_block(provider: HTTPProvider, block_num, tracer, timeout=120):
    params = [block_num, {
        'disableStack': True,
        'disableMemory': True,
        'disableStorage': True,
        'timeout': str(timeout) + 's',
    }]
    if tracer is not None:
        params[1]['tracer'] = tracer
    return provider.make_request('debug_traceBlockByNumber', params)


def fetch_block(provider: HTTPProvider, block_num):
    w3 = Web3(provider)
    w3.toWei
    return w3.eth.get_block(block_num)


def print_stack(stack, tabs):
    print("{}Stack:".format(tabs))
    for item in stack:
        print("\t{0}0x{1}".format(tabs, item))


def print_opcodes(opcodes, tabs=""):
    for opcode in opcodes:
        op = opcode['op']
        if op == 'CALL' or op == 'CALLCODE' or op == 'DELEGATECALL' or op == 'STATICCALL':
            line = "\n{0}Step={1:0>8x} {2:<16}\tpc={3:0>8x} depth={4} return={5}".format(tabs, opcode['step'],
                                                                                         opcode['op'],
                                                                                         opcode['pc'],
                                                                                         opcode['depth'],
                                                                                         opcode['return'])
            print(line)
            print_stack(opcode['stack'], tabs)
            print_opcodes(opcode['ops'], tabs + '\t')
        else:
            line = "\n{0}Step={1:0>8x} {2:<16}\tpc={3:0>8x} depth={4}".format(tabs, opcode['step'], opcode['op'],
                                                                              opcode['pc'],
                                                                              opcode['depth'])
            print(line)
            print_stack(opcode['stack'], tabs)


def extract_access_list(hash, resp):
    if "result" in resp:
        record = {
            'h': hash,
            'type': resp['result']['type'],
            'jumpis': resp['result']['jumpis'],
            'st': resp['result']['st'],
            'tt': resp['result']['tt'],
            'ta': len(resp['result']['acl']),
        }

        a = []
        s = []
        ts = 0
        for address, slots in resp['result']['acl'].items():
            a.append(address)
            if len(slots) > 0:
                keys = []
                for k in slots.keys():
                    keys.append(formalize_slot_key(k))

                slots2 = {'address': address, 'storageKeys': keys}
                ts = ts + len(slots2['storageKeys'])
                s.append(slots2)

        rd = {
            'a': a
        }

        if len(s) > 0:
            rd['s'] = s
        sort_acl_rd(rd)

        record['ts'] = ts
        record['rd'] = [rd]
        return record
    else:
        return {'h': hash}


def extract_block_access_list(block, resp):
    results = []
    if 'transactions' in block and 'result' in resp:
        txs = block['transactions']
        for idx, item in enumerate(resp['result']):
            results.append(extract_access_list(txs[idx].hex(), item))
    return results


def summarize_access_list2(record, acl):
    acl_set = {}
    for address, funcs in acl.items():
        address_slots = set()
        if address in acl_set:
            address_slots = acl_set[address]

        if len(funcs) > 0:
            for func, func_acl in funcs.items():
                for address2, slots in func_acl.items():
                    if "s" == address2:
                        if len(slots) > 0:
                            for slot in slots:
                                address_slots.add(slot)
                    elif address2 not in acl_set:
                        acl_set[address2] = set()

        acl_set[address] = address_slots

    a = []
    s = []
    ts = 0
    ta = len(acl_set)
    for address, slots in acl_set.items():
        a.append(address)
        if len(slots) > 0:
            keys = []
            for k in slots:
                keys.append(k)

            slots2 = {'address': address, 'storageKeys': keys}
            s.append(slots2)
            ts = ts + len(keys)

    rd = {
        'a': a
    }

    if len(s) > 0:
        rd['s'] = s

    sort_acl_rd(rd)

    record['ta'] = ta
    record['ts'] = ts
    record['rd'] = [rd]
    return record


def extract_access_list2(hash, resp, summary=0):
    if "result" in resp:
        record = {
            'h': hash,
            'type': resp['result']['type'],
            'jumpis': resp['result']['jumpis'],
            'st': resp['result']['st'],
            'tt': resp['result']['tt'],
            'status': resp['result']['status'],
        }

        if 'tmp' in resp['result']:
            record['tmp'] = resp['result']['tmp']

        acl = resp['result']['acl']
        for address, funcs in resp['result']['acl'].items():
            if len(funcs) > 0:
                for func, func_acl in funcs.items():
                    new_func_acl = {}
                    for address2, slots in func_acl.items():
                        keys = []
                        if "s" == address2:
                            if len(slots) > 0:
                                for slot in slots.keys():
                                    keys.append(formalize_slot_key(slot))
                        else:
                            keys = list(slots.keys())
                        new_func_acl[address2] = keys
                    funcs[func] = new_func_acl

        if summary == 0:
            record['acl'] = acl
            return record
        else:
            return summarize_access_list2(record, acl)
    else:
        return {'h': hash}


def extract_block_access_list2(block, resp, summary=False):
    results = []
    if 'transactions' in block and 'result' in resp:
        txs = block['transactions']
        for idx, item in enumerate(resp['result']):
            results.append(extract_access_list2(txs[idx].hex(), item, summary))
    return results


def sort_acl_rd(record):
    if 'a' in record:
        record['a'].sort()
    if 's' in record:
        for address_slots in record['s']:
            address_slots['storageKeys'].sort()

        record['s'] = sorted(record['s'], key=lambda x: x['address'])


def formalize_slot_key(slot_key):
    value = int(slot_key, 16)
    return "{0:#0{1}x}".format(value, 66)


def main():
    parser = argparse.ArgumentParser(description='Trace helper')
    parser.add_argument('--rpc', '-r', help='RPC server url, required', required=True)
    parser.add_argument('--tx', help='transaction hash or block number, required', required=True)
    parser.add_argument('--tracer', '-t', help='tracer name, default is ac_tracer2', default='ac_tracer2')
    parser.add_argument('--timeout', '-T', help='tracer timeout, in seconds', default=30)
    parser.add_argument('--summary', '-s', help='get summary information, default is 0', default=0)
    parser.add_argument('--out', '-o',
                        help='tracer output file name prefix, tx and .json will be appended as the full name')

    args = parser.parse_args()

    tracer_name = args.tracer
    tracer = load_tracer(tracer_name)
    http_provider = HTTPProvider(args.rpc, {'timeout': 120})

    block = None
    tx = args.tx
    start_time = datetime.datetime.now()
    if tx.isnumeric():
        # Need to convert it to hex string
        block_num = hex(int(tx))
        block = fetch_block(http_provider, block_num)
        resp = trace_block(http_provider, block_num, tracer)
    else:
        resp = trace_tx(http_provider, tx, tracer)
    end_time = datetime.datetime.now()

    if tracer_name == 'ac_tracer':
        if block is not None:
            result = extract_block_access_list(block, resp)
        else:
            result = extract_access_list(tx, resp)
    elif tracer_name == 'ac_tracer2':
        if block is not None:
            result = extract_block_access_list2(block, resp, int(args.summary))
        else:
            result = extract_access_list2(tx, resp, int(args.summary))
    elif "result" in resp:
        result = resp['result']
    else:
        result = resp

    if args.out is None:
        if tracer_name == 'dis_tracer' and block is None:
            print_opcodes(result)
        else:
            print(json.dumps(result, indent=4))
    else:
        filename = args.out + "-" + tx + ".json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)

    delta = end_time - start_time
    print("\nTrace {0} time {1}s".format(tx, delta.total_seconds()))


if __name__ == '__main__':
    main()
