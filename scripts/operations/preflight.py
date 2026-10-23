"""Inspect a cloud profile without loading local credentials or calling an API."""
import argparse
import json

from campusai.deployment.config.settings import CloudSettings, ConfigurationError
from campusai.deployment.config.preflight import inspect


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='/etc/campusai/deployment.json')
    parser.add_argument('--config-only',action='store_true')
    args = parser.parse_args(argv)
    try:
        settings = CloudSettings.load(args.config)
        report = ({'status':'CONFIG_VALID_ONLY','deployment_accepted':False,
                   'provider_calls':0,'model_loads':0,'filesystem_writes':0}
                  if args.config_only else inspect(settings))
    except ConfigurationError as error:
        report = {'status':'NOT_READY','deployment_accepted':False,'code':error.code,
                  'provider_calls':0,'model_loads':0,'filesystem_writes':0}
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['status'] in {'CONFIG_VALID_ONLY','PREREQUISITES_PASS'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
