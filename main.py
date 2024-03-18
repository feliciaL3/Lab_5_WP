import sys
import argparse
import socket
from urllib.parse import urlparse

def make_http_request(url):
    """
    Makes an HTTP request to the specified URL and returns the response.

    Args:
        url (str): The URL to make the request to.

    Returns:
        str: The response received from the server.
    """
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else '/'

    try:
        with socket.create_connection((host, 80)) as s:
            s.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
            response = b""
            while True:
                data = s.recv(1024)
                if not data:
                    break
                response += data
            return response.decode('utf-8')
    except Exception as e:
        return str(e)

def search(term):
    """
    Searches for the specified term using a predefined search engine.

    Args:
        term (str): The term to search for.

    Returns:
        str: The search results.
    """
    search_url = f"https://developer.mozilla.org/ru/docs/Web/API/WebSockets_API/?q={term}"
    return make_http_request(search_url)

def parse_args():
    """
    Parses command line arguments.

    Returns:
        argparse.Namespace: An object containing parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Web CLI")
    parser.add_argument("-u", "--url", help="Make an HTTP request to the specified URL and print the response")
    parser.add_argument("-s", "--search", help="Search for the term using a predefined search engine and print the results")
    return parser.parse_args()

def main():
    """
    Main function to execute the script.
    """
    args = parse_args()

    if not any(vars(args).values()):
        print("No command-line option specified. Please refer to the usage instructions by running the script with -h or --help.")
        sys.exit()

    if args.url:
        response = make_http_request(args.url)
        print(response)

    elif args.search:
        response = search(args.search)
        print(response)

if __name__ == "__main__":
    main()
