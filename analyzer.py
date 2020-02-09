import argparse
import logging
from urllib.request import Request, urlopen

GH_API_HOST = 'https://api.github.com'
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def router(args):
    if getattr(args, 'org', False):
        logger.debug(args.org)

        req = Request(GH_API_HOST)
        # req.add_header('Referer', 'http://www.python.org/')
        # Customize the default User-Agent header value:
        # req.add_header('User-Agent', 'urllib-example/0.1 (Contact: . . .)')
        r = urlopen(req)
        logger.debug(r)
        return
    print('Nothing')


def main():
    arg_parser = argparse.ArgumentParser(description='GITHUB repo analyzer.')
    arg_parser.add_argument('--org', help='Show a list of repos by an organization')
    # todo debug logging
    args = arg_parser.parse_args()
    router(args)


if __name__ == '__main__':
    main()
