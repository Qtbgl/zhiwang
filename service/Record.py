import pathlib

import bibtexparser
import asyncio

from service.pdf_tools import match_pdf_to_pub, get_pub_info


class Record:
    def __init__(self):
        self.pages = None
        self.fail_pubs = []
        self.filled_pubs = []
        self.pub_infos = []  # 等待下载pdf对应的文献信息

    def new_to_match(self, pub):
        self.pub_infos.append(get_pub_info(pub))

    @property
    def unmatched_pdf_cnt(self):
        return len(self.pub_infos)

    def match_pdf(self, pdf_file: pathlib.Path):
        for pub_info in self.pub_infos:
            if not pub_info['is_matched'] and match_pdf_to_pub(pdf_file.name, pub_info):
                pub_info['is_matched'] = True
                return

    def is_matched(self, pub_url):
        for pub_info in self.pub_infos:
            if pub_info['pub_url'] == pub_url:
                return pub_info['is_matched']

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
