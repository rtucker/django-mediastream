def html_tree(thing):
    out = []
    if type(thing) is list:
        out.append(u'<ul style="margin-left:0;padding-left:0;">')
        for row in thing:
            out.append(u'<li style="list-style-type:none;">{0}</li>'.format(html_tree(row)))
        out.append(u'</ul><br/>')
    elif type(thing) is dict:
        out.append(u'<dl style="margin-left:7em;padding-left:30px;">')
        for key, value in thing.items():
            out.append(u'<dt>{0}</dt><dd>{1}</dd>'.format(key, html_tree(value)))
        out.append(u'</dl><br/>')
    elif type(thing) in [str, unicode]:
        for para in thing.splitlines():
            out.append(u'<p>{0}</p>'.format(para))
    else:
        out.append(html_tree(unicode(thing)))
    return u'\n'.join(out)

# From http://stackoverflow.com/a/2894073/205400
def long_substr(data):
    "Find the longest common string in any arbitrary array of strings"
    substr = ''
    if len(data) > 1 and len(data[0]) > 0:
        for i in range(len(data[0])):
            for j in range(len(data[0])-i+1):
                if j > len(substr) and all(data[0][i:i+j] in x for x in data):
                    substr = data[0][i:i+j]
    return substr
