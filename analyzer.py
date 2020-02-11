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


def print_as_table_2c(rows, title='...'):
    print(title)
    # ('{0: <%s}{1: <5}' % '10').format('123', '45')
    col_size_list = [0, 0]
    prepared_rows = []
    for row in rows:
        cells = []
        for col_num in range(row):
            cell = str(row[col_num])
            cell_len = len(cell)
            cells.append(cell)

            max_length = col_size_list[col_num]
            col_size_list[col_num] = cell_len if cell_len > max_length else max_length
        prepared_rows.append(tuple(cells))


def get_api_response(resource):
    req = Request('{}{}'.format(GH_API_HOST, resource))
    req.add_header('Accept', 'application/vnd.github.v3+json')
    res = urlopen(req)
    # TODO Rate problem
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
    table_data = [(contr['login'], contr['contributions']) for contr in res]


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
