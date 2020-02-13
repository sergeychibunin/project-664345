import argparse
import logging
import json
from urllib.request import Request, urlopen

GH_API_HOST = 'https://api.github.com'
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def print_title(title):
    print('===')
    print(title)


def print_list(_list, title='...'):
    print_title(title)
    list(map(lambda x: print(x), _list))


def print_as_table_2c(rows, title='...'):
    # todo empty rows
    print_title(title)
    col_size_list = [0, 0]
    prepared_rows = []
    for row in rows:
        cells = []
        for col_num in range(2):
            cell = str(row[col_num])
            cell_len = len(cell)
            cells.append(cell)

            max_length = col_size_list[col_num]
            col_size_list[col_num] = cell_len if cell_len > max_length else max_length
        prepared_rows.append(tuple(cells))

    list(map(lambda _row:
             print(('{0: <%s}{1: <%s}' % (str(col_size_list[0] + 1), str(col_size_list[1])))
                   .format(_row[0], _row[1])),
             prepared_rows))


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
    res = urlopen(Request(_url))
    if res.getheader('Server') == 'GitHub.com' \
            and res.getheader('Status') == '200 OK':
        logger.debug('Input URL is valid')
        return True
    logger.debug('Input URL is invalid')
    return False


def get_repo_full_name(_url) -> str:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    """
    if is_repo_url(_url):
        return '/'.join(_url.split('/')[3:5])
    return ''


def get_repos(org):
    """Getting repositories by an organization"""
    res = get_api_response('/orgs/{}/repos'.format(org))
    logger.debug('Repos: {}'.format(res))
    print_list([repo['full_name'] for repo in res], 'Repos:')


def get_repo_contributors(repo):
    """Getting repo's contributors by a fullname

    :param repo: string like 'facebookresearch/cparser'
    :return:
    """
    # todo error 403 on 'https://api.github.com/repos/torvalds/linux/contributors'
    res = get_api_response('/repos/{}/contributors?anon=1&per_page=30'.format(repo))
    return [(contr['login'] if 'login' in contr else '-', contr['contributions'])
            for contr in res]


def get_repo_pull_requests(repo):
    # todo param base (branch)
    res = get_api_response('/repos/{}/pulls?per_page=30&state=all'.format(repo))
    # todo process pages
    prs = {'open': [], 'closed': []}
    for pr in res:
        prs[pr['state']].append(pr)
    return len(prs['open']), len(prs['closed'])


def make_full_analysis(_url) -> bool:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    """
    repo = get_repo_full_name(_url)
    if not repo:
        return False
    print_as_table_2c(get_repo_contributors(repo), 'Contributors')
    print_list(['Open {}, closed {}'.format(*get_repo_pull_requests(repo))], 'Pull requests')
    return True


def router(args):
    if getattr(args, 'org', False):
        logger.debug('The organization: {}'.format(args.org))
        get_repos(args.org)
        return
    if getattr(args, 'url', False):
        logger.debug('The repo\'s URL: {}'.format(args.url))
        if make_full_analysis(args.url):
            return
    print('Nothing')


def main():
    arg_parser = argparse.ArgumentParser(description='GITHUB repo analyzer.')
    arg_parser.add_argument('--org', help='Show a list of repos by an organization')
    arg_parser.add_argument('--url', help='Show a full analysis')
    # todo take token for more request amount (Rate problem)
    # todo debug logging
    args = arg_parser.parse_args()
    router(args)


if __name__ == '__main__':
    main()
