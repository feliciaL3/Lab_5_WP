import argparse
import json
import socket
import ssl
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from bs4 import BeautifulSoup


# def extract_links_from_url(url, max_links=15):
# try:
# response = requests.get(url)
#    response.raise_for_status()
#    html_content = response.text
#    soup = BeautifulSoup(html_content, 'html.parser')
#    links = [link.get('href') for link in soup.find_all('a', href=True)[:max_links]]
#    return links
# except requests.RequestException as e:
#    print("Error extracting links:", e)
#    return None


def make_https_request(url, max_redirects=5, accept="text/html"):
    cached_data = get_cached_data(url)
    if cached_data:
        print("Using cached data for the url:", url)
        print(cached_data)
        return
    #    links = extract_links_from_url(url)
    # if links:
    # print("Extracted links:")
    # for link in links:
    #    print(link)
    # else:
    #    print("Failed to extract links.")
    #    return

    url_parts = url.split('//')[-1].split('/')  # desparte URL-ul după primele două slash-uri // și ia partea de după ele
    host = url_parts[0]  # host
    path = '/' + '/'.join(url_parts[1:])  # pentru a forma calea completă a URL-ului
    port = 443  # Default HTTPS port

    # crearea socket
    with socket.create_connection((host, port)) as client_socket:
        with ssl.create_default_context().wrap_socket(client_socket, server_hostname=host) as secure_socket:
            while max_redirects > 0:  # bucla, va itera până când (max_redirects) devine zero
                # Construim cererea HTTP GET care urmează să fie trimisă la server.
                request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nAccept: {accept}\r\nConnection: close\r\n\r\n"
                secure_socket.sendall(request.encode())  # encode() folosit pentru transf șirul de caractere în octeți

                response = b""  # ițializam var care va stoca răspunsul de la server
                while True:  # Primirea datelor de la server în blocuri de 1024 de octeți
                    part = secure_socket.recv(1024)
                    if not part:  # verificam dacă ultimul bloc de date primit de la server e gol
                        break
                    response += part

                # Redirectionarea
                print("**************************")
                if response:  # divizam răspunsul în linii,apoi preia prima linie care conține status line
                    status_line = response.split(b"\r\n", 1)[0].decode("utf-8")
                    if status_line.startswith("HTTP/1.1"):  # răspuns HTTP valid
                        # impărțim status line-ul în cuvinte (separând după spațiu) și preluăm al doilea cuvânt
                        status_code = int(status_line.split()[1])
                    else:
                        print("Invalid HTTP response:", status_line)
                        return
                else:
                    return
                print("Status code:", status_code)

                if 300 <= status_code < 400:
                    max_redirects -= 1
                    redirect_url = extract_redirect_url(response)
                    if not redirect_url:
                        print("error, no url found")
                        break
                    print("Redirecting to:", redirect_url)
                    make_https_request(redirect_url)
                else:
                    break

    if 200 <= status_code < 300:
        print("Success:")
    else:
        print("Failure:")

    # content type from header
    headers = response.split(b"\r\n\r\n", 1)[0].decode("utf-8")
    # print("Response headers:", headers)
    content_type = None
    for header in headers.split("\r\n"):
        if header.startswith("Content-Type:"):
            content_type = header.split(":")[1].strip()
            break

    # process the response based on content type html or json
    if content_type == "application/json":
        json_content = json.loads(response.split(b"\r\n\r\n", 1)[1].decode("utf-8"))
        print(json_content)
        relevant_content = json_content
    else:
        try:
            html_content = response.decode('utf-8')
        except UnicodeDecodeError:
            html_content = response.decode('ISO-8859-1')

        # extract the content
        soup = BeautifulSoup(html_content, 'html.parser')
        relevant_content = soup.get_text()

        print(relevant_content)

    # cache the fetched data
    cache_data(url, relevant_content)


# load cached data from a JSON file
def load_cache():
    try:
        with open("cache.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# save cached data to file
def save_cache(cache):
    with open("cache.json", "w") as f:
        json.dump(cache, f, indent=4)


# retrieve data from file
def get_cached_data(url):
    cache = load_cache()
    cached_data = cache.get(url)
    if cached_data:
        cached_time = datetime.fromisoformat(cached_data["timestamp"])
        if datetime.now() - cached_time < timedelta(hours=1):
            return cached_data["content"]
        else:
            # delete expired content from file
            del cache[url]
            save_cache(cache)
    return None


# cache fetched data
def cache_data(url, content):
    cache = load_cache()
    cache[url] = {"timestamp": datetime.now().isoformat(), "content": content}
    save_cache(cache)


def extract_redirect_url(response):
    headers, _, body = response.partition(b'\r\n\r\n')
    for line in headers.split(b'\r\n'):
        if line.startswith(b'Location:'):
            link = line.split(b':', 1)[1].strip().decode()
            return link
    return None


def search_google(search_term):
    try:
        encoded_search = quote_plus(search_term)
        request_url = f"/search?q={encoded_search}"

        with socket.create_connection(("www.google.com", 80)) as client_socket:
            request = f"GET {request_url} HTTP/1.1\r\nHost: www.google.com\r\nConnection: close\r\n\r\n"
            client_socket.sendall(request.encode())

            response = b""
            while True:
                part = client_socket.recv(1024)
                if not part:
                    break
                response += part

        try:
            html_content = response.decode('utf-8')
        except UnicodeDecodeError:
            html_content = response.decode('ISO-8859-1')

        soup = BeautifulSoup(html_content, 'html.parser')
        count = 0
        for index, div in enumerate(soup.find_all('div', class_='egMi0 kCrYT'), 1):
            link_element = div.find('a', href=True)
            title_element = div.find('h3', class_='zBAuLc l97dzf')
            if link_element and title_element:
                title = title_element.get_text(strip=True)
                link = link_element['href']

                # extract only link from "http" until "/&"
                start_index = link.find("http")
                end_index = link.find("&")
                if start_index != -1 and end_index != -1:
                    link = link[start_index:end_index]

                print(" * \033[92m", title, "\033[0m",  " - ", link)

                count += 1
                if count >= 10:
                    break

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creating HTTP requests and retrieving content from websites")
    parser.add_argument("-u", "--url", help="Make an HTTP request to the specified URL and print the response")
    parser.add_argument("-s", "--search", help="Make an HTTP request to search the term  and print top 10 results")
    args = parser.parse_args()

    if args.url:
        make_https_request(args.url)
    elif args.search:
        search_google(args.search)
    else:
        print("Input parameter")
