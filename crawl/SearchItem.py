class SearchItem:
    def __init__(self, name, pages=None, sort_by=None, year=None, min_cite=None):
        """
        :param pages: 爬取多少页的文献
        :param name: 搜索关键词
        :param sort_by: 排序根据 relevant, date, cite, download
        :param year: 发表年份
        :param min_cite: 引用数量过滤
        """
        self.name = name
        self.pages = pages
        self.sort_by = sort_by
        self.year = year
        self.min_cite = min_cite

    def __str__(self):
        return str(self.__dict__)
