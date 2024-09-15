import bibtexparser
import asyncio


class Record:
    def __init__(self):
        self.pages = None
        self.fail_pubs = []
        self.filled_pubs = []
        self.pdf_cnt = 0  # 等待下载数量

    def set_pages(self, pages):
        self.pages = pages

    async def fail_to_fill(self, pub):
        self.fail_pubs.append(pub)

    async def success_fill(self, pub):
        self.filled_pubs.append(pub)

    def get_progress(self):
        if not self.pages:
            return 0.0

        total = 20 * self.pages  # debug 每一页20篇
        done = len(self.filled_pubs) + len(self.fail_pubs)
        return done / total

    def deliver_pubs(self):
        all_pubs = self.filled_pubs + self.fail_pubs
        results = [self._deliver(pub) for pub in all_pubs]
        return results

    def _deliver(self, pub):
        abstract = pub.get('abstract')
        bib_str = pub.get('bib')
        # 组合摘要到bib中
        if bib_str and abstract:
            bib_db = bibtexparser.loads(bib_str)
            entry = bib_db.entries[0]
            entry['abstract'] = pub['abstract']
            bib_str = bibtexparser.dumps(bib_db)

        return {
            'abstract': abstract,
            'pub_url': pub['url'],
            'title': pub['title'],
            'author': pub['author'],
            'date': pub['date'],
            'num_citations': pub.get('num_citations', None),
            # 'pdf_link': pub.get('pdf_link'),  # 必须从页面中跳转进入
            'bib_link': pub.get('bib_link'),
            'bib': bib_str,
            'error': pub.get('error'),
        }
