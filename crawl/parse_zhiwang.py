from bs4 import BeautifulSoup


def parse_result_page(html_str):
    soup = BeautifulSoup(html_str, 'html.parser')
    pubs = []
    for tr in soup.select('#ModuleSearchResult tbody > tr'):
        name = tr.find('td', class_='name')
        author = tr.find('td', class_='author')
        # author = [a.text for a in author.find_all('a', class_='KnowledgeNetLink', target='knet')]
        # author = ', '.join(author)
        author = author.text.strip()
        source = tr.find('td', class_='source')
        date = tr.find('td', class_='date')
        data = tr.find('td', class_='data')
        quote = tr.find('td', class_='quote')
        pub = {
            'url': name.a['href'],
            'title': name.a.text,
            'author': author,
            'source': source.text.strip(),
            'date': date.text,
            'pub_type': data.text.strip(),
            'num_citation': int(quote.text) if quote.text.strip() else None,
        }
        pubs.append(pub)

    return pubs
