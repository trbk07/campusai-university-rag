"""Subprocess quota fixture. No provider/network/model invocation."""
import json
import sys
from campusai.llm.quota import QuotaGovernor, QuotaPolicy, QuotaExceeded


def main():
    governor = QuotaGovernor(sys.argv[1], 'subprocess-test',
                             QuotaPolicy(0, requests_per_day=3, max_in_flight=6), max_wait_seconds=0)
    try:
        reservation = governor.reserve(10, 10, lease_seconds=20)
    except QuotaExceeded:
        print(json.dumps({'admitted':False}))
    else:
        governor.finish(reservation)
        print(json.dumps({'admitted':True}))


if __name__ == '__main__':
    main()
