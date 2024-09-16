import re


def get_pub_info(pub):
    return {
        'title': pub['title'],
        'author': pub['author'],
        'pub_url': pub['url'],  # 用于区分pubs
        'is_matched': False,
    }


def match_pdf_to_pub(pdf_file: str, pub_info: dict):
    """
    :param pdf_file: 不带路径，文件名
    :param pub_info:
    :return:
    """
    parts_of_chinese = re.findall(r'[\u4e00-\u9fa5]+', pdf_file)
    full_info = pub_info['title'] + ' ' + pub_info['author']
    for part in parts_of_chinese:
        if part not in full_info:
            return False
    return True
