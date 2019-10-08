def truncatechars(text, count=20, ellipsis=u'..'):
    """ Returns an unicode.

    Truncates the `text` making it `count` in length
    and suffixing it with the `ellipsis`.
    """
    if len(text) <= count:
        return text
    return u'{}{}'.format(text[:count - len(ellipsis)], ellipsis)
