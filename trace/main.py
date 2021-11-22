# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import sys
import json
from web3 import HTTPProvider

from trace.tracer.tracer import load_tracer


def trace_tx(provider: HTTPProvider, tx_hash, tracer):
    params = [tx_hash, {
        'disableStack': False,
        'disableMemory': False,
        'disableStorage': True}]
    if tracer is not None:
        params[1]['tracer'] = tracer
    return provider.make_request('debug_traceTransaction', params)


def print_help():
    help_str = '''
        Usage: pipenv run main.py provider_url tx_hash [tracer]
        tracer is optional, its value could be ac_tracer or dis_tracer, 
        '''
    print(help_str)


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print_help()
        sys.exit(-1)

    url = sys.argv[1]
    tx = sys.argv[2]

    if len(sys.argv) > 3:
        tracer = load_tracer(sys.argv[3])
    else:
        tracer = None

    http_provider = HTTPProvider(url)
    resp = trace_tx(http_provider, tx, tracer)

    print(json.dumps(resp, indent=4))
