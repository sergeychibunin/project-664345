import unittest
import sys
import io
import argparse
import datetime
import logging
import json
from argparse import ArgumentParser, Namespace
from typing import Union, Text, Sequence, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from contextlib import contextmanager

GH_API_HOST = 'https://api.github.com'
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
notifications = set()


@contextmanager
def __test_stdout():
    old_stdout, new_stdout = sys.stdout, io.StringIO()
    try:
        sys.stdout = new_stdout
        yield sys.stdout
    finally:
        sys.out = old_stdout


class _ArgDebugAction(argparse.Action):

    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: Union[Text, Sequence[Any], None],
                 option_string: Optional[Text] = ...) -> None:
        global logger
        logger.setLevel(logging.DEBUG)


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


def add_notification(msg):
    global notifications
    notifications.add(msg)


def get_api_response(resource):
    req = Request('{}{}'.format(GH_API_HOST, resource))
    req.add_header('Accept', 'application/vnd.github.v3+json')
    # req.add_header('Authorization', 'token ...')
    try:
        # TODO Rate problem (if you need to run the analyzer many times in hour)
        res = urlopen(req)
        links = res.getheader('Link') or ''
    except HTTPError:
        # todo GH messages
        # todo error 403 on 'https://api.github.com/repos/torvalds/linux/contributors' (contributor list is too large)
        add_notification('The API not available. Try again later.')
        return [], ''
    return json.loads(res.read().decode('utf-8')), links


def is_repo_url(_url) -> bool:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    """
    try:
        res = urlopen(Request(_url))
    except HTTPError:
        add_notification('The API not available. Try again later.')
        return False

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
    res, _ = get_api_response('/orgs/{}/repos'.format(org))
    logger.debug('Repos: {}'.format(res))
    print_list([repo['full_name'] for repo in res], 'Repos:')


def get_repo_contributors(repo):
    """Getting repo's contributors by a fullname

    :param repo: string like 'facebookresearch/cparser'
    :return:
    """
    res, _ = get_api_response('/repos/{}/contributors?anon=1&per_page=30'.format(repo))
    return [(contr['login'] if 'login' in contr else '-', contr['contributions'])
            for contr in res]


def get_repo_data(repo, category: str, eld: int, branch=None, b_date=None, e_date=None):
    """
    :param category: a string like 'pulls' or 'issues'
    """
    additional_params = ''
    if branch and category == 'pulls':
        additional_params = '&base={}'.format(branch)

    page = 1
    is_run = True
    pages = []
    while is_run:
        # API do not have special parameters for filtering by dates what we need
        res, links = get_api_response('/repos/{}/{}?page={}&per_page=30&state=all{}'.
                                      format(repo, category, page, additional_params if additional_params else ''))
        pages += res
        try:
            links.index('rel="next"')
            page += 1
        except ValueError:
            is_run = False

    prs = {'open': [], 'closed': [], 'old': []}
    date_from = b_date if b_date else datetime.datetime(1970, 1, 1)
    date_to = e_date if e_date else datetime.datetime.today()
    limit = datetime.timedelta(eld)

    for pr in pages:
        pr_created = datetime.datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        if date_from > pr_created or pr_created >= date_to:
            continue

        pr_closed = datetime.datetime.strptime(pr['closed_at'], '%Y-%m-%dT%H:%M:%SZ') if pr['closed_at'] else None
        is_closed = False
        if pr_closed and pr_closed <= date_to:
            is_closed = True

        if is_closed:
            prs['closed'].append(pr)
        else:
            prs['open'].append(pr)

        if not is_closed and date_to - pr_created >= limit:
            prs['old'].append(pr)

    return len(prs['open']), len(prs['closed']), len(prs['old'])


def make_full_analysis(_url, branch: str, b_date: datetime.datetime, e_date: datetime.datetime) -> bool:
    """
    :param _url: string like 'https://github.com/facebookresearch/cparser'
    """
    repo = get_repo_full_name(_url)
    if not repo:
        return False
    print_as_table_2c(get_repo_contributors(repo), 'Contributors')
    print_list(['Open {}, closed {}, old {}'.
               format(*get_repo_data(repo, 'pulls', 30, branch, b_date, e_date))], 'Pull requests')
    print_list(['Open {}, closed {}, old {}'.
               format(*get_repo_data(repo, 'issues', 14, b_date=b_date, e_date=e_date))], 'Issues')
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
        if make_full_analysis(args.url, args.branch, args.b_date, args.e_date):
            return
    print('Nothing')


def main():
    def valid_date(s):
        try:
            return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            msg = "Not a valid date: '{0}'.".format(s)
            raise argparse.ArgumentTypeError(msg)

    def is_valid_args(_args):
        if _args.b_date and _args.e_date and _args.b_date >= _args.e_date:
            add_notification('Not valid dates')
            return False
        return True

    arg_parser = argparse.ArgumentParser(description='GITHUB repo analyzer.')
    arg_parser.add_argument('--org', help='Show a list of repos by an organization')
    arg_parser.add_argument('--url', help='Show a full analysis')
    arg_parser.add_argument('--branch', help='Specify a branch. There is a default: master')
    arg_parser.add_argument('--beginning-date', type=valid_date, dest='b_date',
                            help='Specify a beginning date like \'YYYY-MM-DD HH:MM:SS\'. It is an optional')
    arg_parser.add_argument('--end-date', type=valid_date, dest='e_date',
                            help='Specify an end date like \'YYYY-MM-DD HH:MM:SS\'. It is an optional')
    arg_parser.add_argument('--self-checking',
                            dest='maintenance', help='Run a tool\'s maintenance', action='store_true')
    arg_parser.add_argument('--debug', action=_ArgDebugAction, type=bool)
    args = arg_parser.parse_args()
    if is_valid_args(args):
        router(args)
    print_list(notifications, 'System notifications') if notifications else None


if __name__ == '__main__':
    main()
