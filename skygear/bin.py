# Copyright 2015 Oursky Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import sys
from importlib.machinery import SourceFileLoader

from .container import SkygearContainer
from .options import parse_args
from .registry import get_registry
from .transmitter import ConsoleTransport, ZmqTransport

log = logging.getLogger(__name__)


def main():
    options = parse_args()
    setup_logging(options)
    run_plugin(options)


def run_plugin(options):
    if not options.plugin:
        log.error("Usage: py-skygear plugin.py")
        sys.exit(1)
    SourceFileLoader('plugin', options.plugin).load_module()

    SkygearContainer.set_default_app_name(options.appname)
    SkygearContainer.set_default_endpoint(options.skygear_endpoint)
    SkygearContainer.set_default_apikey(options.apikey)

    if options.subprocess is not None:
        return stdin(options.subprocess)

    log.info(
        "Connecting to address %s" % options.skygear_address)
    transport = ZmqTransport(options.skygear_address)
    transport.run()


def stdin(_input):
    target = _input[0]
    if target not in ['init', 'op', 'hook', 'handler', 'timer', 'provider']:
        print(
            "Only init, op, hook, handler, timer and provider is support now",
            file=sys.stderr)
        sys.exit(1)
    transport = ConsoleTransport()
    if target == 'init':
        json.dump(get_registry().func_list(), sys.stdout)
    elif len(_input) < 2:
        print("Missing param for %s", target, file=sys.stderr)
        sys.exit(1)
    else:
        transport.handle_call(target, *_input[1:])


def setup_logging(options):
    # TODO: Make it load a stadard python logging config.
    logger = logging.getLogger()
    level = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }.get(options.loglevel, logging.INFO)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('''\
%(asctime)s %(levelname)-5.5s \
[%(name)s:%(lineno)s][%(threadName)s] %(message)s\
''')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
