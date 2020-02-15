import unittest
import sys
import io
import argparse
import datetime
import logging
import json
from urllib.request import Request, urlopen
from contextlib import contextmanager

GH_API_HOST = 'https://api.github.com'
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@contextmanager
def __test_stdout():
    old_stdout, new_stdout = sys.stdout, io.StringIO()
    try:
        sys.stdout = new_stdout
        yield sys.stdout
    finally:
        sys.out = old_stdout


class TestViewLevelFunctions(unittest.TestCase):

    def test_print_title(self):
        """Test prints out formatted lines as a block's title"""
        with self.assertRaises(TypeError):
            print_title()

        with globals()['__test_stdout']() as out:
            print_title('!')
        self.assertEqual(out.getvalue(), '===\n!\n')

    def test_print_list(self):
        """Test prints out formatted lines as a block with a title"""
        with self.assertRaises(TypeError):
            print_list()

        with globals()['__test_stdout']() as out:
            print_list([])
        self.assertEqual(out.getvalue(), '===\n...\n')

        with globals()['__test_stdout']() as out:
            print_list(['!', '!'], title='>')
        self.assertEqual(out.getvalue(), '===\n>\n!\n!\n')

    def test_print_as_table_2c(self):
        """Test prints out formatted lines as a table with 2 auto-sized columns"""
        with self.assertRaises(TypeError):
            print_as_table_2c()

        with self.assertRaises(AssertionError):
            print_as_table_2c([(1,)])

        with self.assertRaises(AssertionError):
            print_as_table_2c([(1, 2, 3)])

        with globals()['__test_stdout']() as out:
            print_as_table_2c([])
        self.assertEqual(out.getvalue(), '===\n...\nEmpty\n')

        with globals()['__test_stdout']() as out:
            print_as_table_2c([(1, 2)], title='!')
        self.assertEqual(out.getvalue(), '===\n!\n1 2\n')

        with globals()['__test_stdout']() as out:
            print_as_table_2c([(1, 2), (100, 2)], title='!')
        self.assertEqual(out.getvalue(), '===\n!\n1   2\n100 2\n')


def __run_tests():
    suite = unittest.TestSuite()
    suite.addTest(TestViewLevelFunctions('test_print_title'))
    suite.addTest(TestViewLevelFunctions('test_print_list'))
    suite.addTest(TestViewLevelFunctions('test_print_as_table_2c'))
    runner = unittest.TextTestRunner()
    runner.run(suite)


def print_title(title):
    print('===')
    print(title)


def print_list(_list, title='...'):
    print_title(title)
    list(map(lambda x: print(x), _list))


def print_as_table_2c(rows, title='...'):
    print_title(title)

    if not rows:
        print('Empty')
        return

    col_size_list = [0, 0]
    prepared_rows = []
    for row in rows:
        assert len(row) == 2
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
    :return: repo's full name like 'facebookresearch/cparser'
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
    res = get_api_response('/repos/{}/contributors?anon=1&per_page=30'.format(repo))  # todo sort
    return [(contr['login'] if 'login' in contr else '-', contr['contributions'])
            for contr in res]


def get_repo_data(repo, category: str, eld: int):
    """
    :param category: a string like 'pulls' or 'issues'
    """
    # todo param base (branch)
    res = get_api_response('/repos/{}/{}?per_page=30&state=all'.format(repo, category))
    # todo process pages
    prs = {'open': [], 'closed': [], 'old': []}
    now = datetime.datetime.today()  # todo user date arg
    limit = datetime.timedelta(eld)
    for pr in res:
        prs[pr['state']].append(pr)
        pr_created = datetime.datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        if pr['state'] == 'open' and now - pr_created >= limit:
            prs['old'].append(pr)
    return len(prs['open']), len(prs['closed']), len(prs['old'])


def make_full_analysis(_url) -> bool:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    """
    repo = get_repo_full_name(_url)
    if not repo:
        return False
    print_as_table_2c(get_repo_contributors(repo), 'Contributors')
    print_list(['Open {}, closed {}, old {}'.format(*get_repo_data(repo, 'pulls', 30))], 'Pull requests')
    print_list(['Open {}, closed {}, old {}'.format(*get_repo_data(repo, 'issues', 14))], 'Issues')
    return True


def router(args):
    if getattr(args, 'maintenance', False):
        __run_tests()
        return
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
    arg_parser.add_argument('--self-checking',
                            dest='maintenance', help='Run a tool\'s maintenance', action='store_true')
    # todo take token for more request amount (Rate problem)
    # todo debug logging
    args = arg_parser.parse_args()
    router(args)


if __name__ == '__main__':
    main()
