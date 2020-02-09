import argparse
import logging
import json
from urllib.request import Request, urlopen

GH_API_HOST = 'https://api.github.com'
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def print_list(_list, title='...'):
    print(title)
    list(map(lambda x: print(x), _list))


def get_api_response(resource):
    req = Request('{}{}'.format(GH_API_HOST, resource))
    req.add_header('Accept', 'application/vnd.github.v3+json')
    res = urlopen(req)
    return json.loads(res.read().decode('utf-8'))


def is_repo_url(_url) -> bool:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    """
    res = urlopen(Request(_url)).read()
    if res.get_header('Server') == 'GitHub.com' \
            and res.get_header('Status') == '200 OK':
        logger.debug('Input URL is valid')
        return True
    logger.debug('Input URL is invalid')
    return False


def get_repo_full_name(_url) -> str:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    :return:
    """
    if is_repo_url(_url):
        return _url.split('/')[2:4]
    return ''


def get_repos(org):
    """Getting repositories by an organization"""
    res = get_api_response('/orgs/{}/repos'.format(org))
    logger.debug('Repos: {}'.format(res))
    print_list([repo['full_name'] for repo in res], 'Repos:')


def get_repo_contributors(_url):
    """Getting repo's contributors by a public URL

    :param _url: string like 'https://github.com/facebookresearch/cparser'
    :return:
    """
    # todo error 403 on 'https://api.github.com/repos/torvalds/linux/contributors'
    res = get_api_response('/repos/{}/contributors?anon=1&per_page=30'.format('/'.join(get_repo_full_name(_url))))


def router(args):
    if getattr(args, 'org', False):
        logger.debug('The organization: {}'.format(args.org))
        get_repos(args.org)
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
