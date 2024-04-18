import sys
import socket
import ssl
import json
import hashlib
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query

cache_file = "cache.json"
db = TinyDB(cache_file)


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


def cache_response(url, response):
    if 'text/html' in response:
        parsed_response = parse_html(response)
    else:
        parsed_response = response

    db.insert({'url': hash_url(url), 'response': parsed_response})


def is_cached(url):
    return db.contains(Query().url == hash_url(url))


def retrieve_cached_response(url):
    result = db.get(Query().url == hash_url(url))
    return result['response']


def print_cached_response(response):
    if isinstance(response, list):
        for item in response:
            print(item)
    elif isinstance(response, str):
        print("Modified JSON Response:")
        try:
            json_data = json.loads(response.split('\r\n\r\n', 1)[1])
            print(json.dumps(json_data, indent=4))  # Print JSON data with indentation
        except json.JSONDecodeError as e:
            print("Error: Unable to parse JSON data:", e)
    else:
        print("Unknown response type")


def extract_url_data(url):
    parsed_url = urlparse(url)

    port = None
    if parsed_url.scheme == "https":
        port = 443
    elif parsed_url.scheme == "http":
        port = 80

    return parsed_url.netloc, port, parsed_url.path


def make_http_request(url):
    if is_cached(url):
        print("Retrieving cached response:", url)
        return retrieve_cached_response(url)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    host, port, path = extract_url_data(url)
    print("Establishing connection:", host, port, path)

    if port == 443:
        context = ssl.create_default_context()
        client_socket = context.wrap_socket(client_socket, server_hostname=host)

    try:
        client_socket.settimeout(2)
        client_socket.connect((host, port))

        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
        client_socket.send(request.encode())

        response = b""
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                response += data

            except socket.timeout:
                break

        resp_data = response.decode('utf-8', errors='ignore')
        cache_response(url, resp_data)

        return resp_data

    finally:
        client_socket.close()


def handle_html_or_json(url):
    if is_cached(url):
        print("Retrieving cached response for:", url)
        response = retrieve_cached_response(url)
        print_cached_response(response)
        return response
    else:
        response = make_http_request(url)
        if 'text/html' in response:
            try:
                parsed_response = parse_html(response)
                cache_response(url, parsed_response)
                return parsed_response
            except Exception as e:
                print("Error: Unable to parse HTML data:", e)
        elif 'application/json' in response:
            try:
                json_data = json.loads(response.split('\r\n\r\n', 1)[1])
                print("Modified JSON Response:")
                print(json.dumps(json_data, indent=4))  # Modified JSON output
                return json_data
            except json.JSONDecodeError as e:
                print("Error: Unable to parse JSON data:", e)
        else:
            print(response)


def parse_html(response):
    soup = BeautifulSoup(response, 'html.parser')
    all_elements = soup.find_all(['h1', 'h2', 'h3', 'p'])
    all_info = []
    for element in all_elements:
        if element.name.startswith('h'):
            depth = len(element.name) - 1  # Depth based on heading level
            tag = f"[{element.name}]"
            stars = '*' * (4 - depth)  # Adjusting the number of asterisks
            all_info.append(f"{stars} {tag} {element.get_text()}")  # Customized representation
        elif element.name == 'p':
            tag = f"[{element.name}]"
            all_info.append(f"* {tag} {element.get_text()}")

    links = soup.find_all('a', href=True)
    links_href = [link['href'] for link in links if link['href'].startswith('http')]
    all_info.append("-- Links --")
    all_info += links_href

    return all_info


def make_google_search(search_term):
    host = "www.google.com"
    search_query = quote(search_term)
    path = f"/search?q={search_query}"
    try:
        context = ssl.create_default_context()
        with context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host) as s:
            s.connect((host, 443))
            request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            s.sendall(request.encode())
            response = b''
            while True:
                data = s.recv(1024)
                if not data:
                    break
                response += data
        response_str = response.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(response_str, 'html.parser')
        links = soup.find_all('a')
        search_results = []
        for link in links:
            href = link.get('href')
            if href.startswith('/url?q='):
                url = href.split('/url?q=')[1].split('&')[0]
                title = link.get_text()  # Extrage titlul linkului
                search_results.append((title, url))
                if len(search_results) >= 10:
                    break
        return search_results
    except Exception as e:
        return f"Error: {str(e)}"


def search(term):
    search_results = make_google_search(term)
    if isinstance(search_results, list):
        print("Search results for", term, ":")
        for i, (title, url) in enumerate(search_results, start=1):
            print(f"{i}. \033[92m{title}\033[0m: {url}")
    else:
        print("Error:", search_results)


def print_error():
    print("No option provided.")
    print("Usage: ")
    print("python go2web.py -u URL")
    print("python go2web.py -s SEARCH_TERM")
    print("python go2web.py -h")
    sys.exit()


def main():
    args = sys.argv[1:]

    if not args:
        print_error()

    if '-u' in args:
        url_index = args.index('-u') + 1
        if url_index < len(args):
            url = args[url_index]
            response = handle_html_or_json(url)
            print("Information extracted from", url, ".")
            if isinstance(response, list):
                for info in response:
                    print(info)
            elif isinstance(response, dict):
                pass
        else:
            print("Error: No URL provided after -u")
            sys.exit()

    elif '-s' in args:
        search_index = args.index('-s') + 1
        if search_index < len(args):
            term = ' '.join(args[args.index('-s') + 1:]) if '-s' in args else None
            if term:
                search(term)
            else:
                print("Error: No search term provided after -s")
                sys.exit()

    elif '-h' in args:
        print("go2web -u <URL>         # Make an HTTP request to the specified URL and print the response")
        print("go2web -s <search-term> # Make an HTTP request to search the term  and print top 10 results")
        print("go2web -h               # Show this help guide ")


if __name__ == "__main__":
    main()
