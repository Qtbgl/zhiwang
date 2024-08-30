from app.param_tools import Params


def create_item(name: str, p: Params):
    return Item(name, p.pages, p.sort_by, p.year)


class Item:
    def __init__(self, name, pages=None, sort_by=None, year=None):
        """
        :param pages: 爬取多少页的文献
        :param name: 搜索关键词
        :param sort_by: 排序根据 relevant, date, cite
        :param year:
        """
        self.name = name
        self.pages = pages
        self.sort_by = sort_by
        self.year = year

    def __str__(self):
        return str(self.__dict__)