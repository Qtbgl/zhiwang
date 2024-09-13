class Record:
    def __init__(self):
        self.pages = None
        self.fail_pubs = []
        self.filled_pubs = []

    def set_pages(self, pages):
        self.pages = pages

    def fail_to_fill(self, pub):
        self.fail_pubs.append(pub)

    def success_fill(self, pub):
        self.filled_pubs.append(pub)

    def get_progress(self):
        if not self.pages:
            return 0.0

        total = 20 * self.pages  # debug 每一页20篇
        done = len(self.filled_pubs) + len(self.fail_pubs)
        return done / total

    def deliver_pubs(self):
        all_pubs = self.filled_pubs + self.fail_pubs
        results = []
        for pub in all_pubs:
            abstract = pub.get('abstract')
            results.append({
                'abstract': abstract,
                'pub_url': pub['url'],
                'title': pub['title'],
                'author': pub['author'],
                'date': pub['date'],
                'num_citations': pub.get('num_citations', None),
                'bib_link': pub.get('bib_link'),
                'bib': pub.get('bib'),
                'error': pub.get('error'),
            })

        return results
