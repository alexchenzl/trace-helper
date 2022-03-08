import json
from pathlib import Path
import argparse
import psycopg2
from configparser import ConfigParser


# Import predictor and access list tracer results into a postgresql database block by block

def match_accounts(p_accounts, t_accounts):
    s = set(t_accounts)
    i = 0
    for account in p_accounts:
        if account in s:
            i += 1
    return i


def match_slots(p_slots, t_slots):
    d = {}
    for address_keys in t_slots:
        s = set(address_keys['storageKeys'])
        d[address_keys['address']] = s

    i = 0
    for address_keys in p_slots:
        if address_keys['address'] in d:
            for key in address_keys['storageKeys']:
                if key in d[address_keys['address']]:
                    i += 1
    return i


def config(filename, section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)

    # get section, default to postgresql
    db_config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_config[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db_config


def parse_block(conn, predictor_prefix, tracer_prefix, block_num, dry=0):
    postfix = "-" + str(block_num) + ".json"
    predictor_file = predictor_prefix + postfix
    tracer_file = tracer_prefix + postfix

    p_sql = "INSERT INTO predict(hash, block, total_touches,total_rounds, total_accounts, " \
            "total_slots, round_batches, accounts, slots, stat_time,matched_accounts, matched_slots,ratio_accounts," \
            "ratio_slots ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    t_sql = "INSERT INTO trace(hash, block, type, jumpis, total_touches, total_accounts, " \
            "total_slots,accounts, slots, stat_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s )"

    # Usually happens when the block is an empty block
    if not Path(predictor_file).is_file():
        raise Exception("Predictor result file {0} doesn't exist ".format(predictor_file))
    if not Path(tracer_file).is_file():
        raise Exception("Tracer result file {0} doesn't exist ".format(tracer_file))

    cur = None
    try:
        tx_hash = None
        if dry == 0:
            cur = conn.cursor()
        with open(predictor_file) as fp_predictor, open(tracer_file) as fp_tracer:
            predictor_results = json.load(fp_predictor)
            tracer_results = json.load(fp_tracer)
            if len(predictor_results) != len(tracer_results):
                raise Exception("Lengths of predictor or tracer results of block {} are not equal")

            for i in range(0, len(predictor_results)):
                p_result = predictor_results[i]
                t_result = tracer_results[i]

                if p_result['h'] != t_result['h']:
                    raise Exception("The {}th tx of block {} in predictor and tracer results are different")

                tx_hash = p_result['h']

                p_accounts = p_result['rd'][0].get('a', [])
                p_slots = p_result['rd'][0].get('s', [])

                t_accounts = t_result['rd'][0].get('a', [])
                t_slots = t_result['rd'][0].get('s', [])

                ratio_accounts = 0
                ratio_slots = 0
                if t_result['type'] == 0:
                    matched_accounts = 2
                    matched_slots = 0
                else:
                    matched_accounts = match_accounts(p_accounts, t_accounts)
                    if matched_accounts > 0:
                        ratio_accounts = matched_accounts / t_result['ta']

                    matched_slots = match_slots(p_slots, t_slots)
                    if matched_slots > 0:
                        ratio_slots = matched_slots / t_result['ts']

                if t_result['st'][-1] == 's':
                    last_two_chars = t_result['st'][-2:]
                    if last_two_chars == 'ns':
                        t_stat_time = int(t_result['st'][:-2])
                    elif last_two_chars == 'ms':
                        t_stat_time = int(float(t_result['st'][:-2]) * 1000000)
                    elif last_two_chars == 'µs':
                        t_stat_time = int(float(t_result['st'][:-2]) * 1000)
                    else:
                        t_stat_time = int(float(t_result['st'][:-1]) * 1000000000)
                else:
                    raise Exception('Failed to parse trace time {0}:{1} {2}'.format(block_num, tx_hash, t_result['st']))

                if dry == 0:
                    cur.execute(p_sql, (
                        tx_hash, block_num, p_result['tt'], p_result['tr'], p_result['ta'], p_result['ts'],
                        json.dumps(p_result['rb']), json.dumps(p_accounts), json.dumps(p_slots),
                        p_result['st'], matched_accounts, matched_slots, ratio_accounts, ratio_slots))

                    cur.execute(t_sql, (
                        tx_hash, block_num, t_result['type'], t_result['jumpis'], t_result['tt'], t_result['ta'], t_result['ts'],
                        json.dumps(t_accounts), json.dumps(t_slots), t_stat_time))

                    conn.commit()
            return len(predictor_results)
    except Exception as e:
        raise Exception('Failed to parse block {0}:{1} {2}'.format(block_num, tx_hash, e))
    finally:
        if cur is not None:
            cur.close()


def import_data(conn, predictor_prefix, tracer_prefix, begin_block, end_block, dry=0):
    for block_num in range(begin_block, end_block):
        try:
            parse_block(conn, predictor_prefix, tracer_prefix, block_num, dry)
            print("block {} parsed".format(block_num))
        except Exception as e:
            print("failed to parse block {}: {}".format(block_num, e))


def main():
    args = arg_parser.parse_args()

    conn = None
    try:
        # read connection parameters
        params = config(args.db)
        conn = psycopg2.connect(**params)

        import_data(conn, args.predictor, args.tracer, int(args.begin), int(args.end), args.dry)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Import predictor and access list tracer results into database block by block')
    arg_parser.add_argument('--db', '-d', help='database ini config file name', default='database.ini')
    arg_parser.add_argument('--predictor', '-p', help='predictor result file prefix with path', required=True)
    arg_parser.add_argument('--tracer', '-t', help='tracer result file prefix with path', required=True)
    arg_parser.add_argument('--begin', '-b', help='begin block number ( including )', required=True)
    arg_parser.add_argument('--end', '-e', help='end block number ( excluded )', required=True)
    arg_parser.add_argument('--dry', '-D', help='dry run, only parse data but not insert them into database', default=0)
    main()
