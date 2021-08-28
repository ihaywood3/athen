from registry import *

import re, logging

def replace_lines(m):
    print("got line %r" % m.group(0))
    return m.group(0)

def process_text(data,ld):
    data = re.sub(r'\*([^0-9*\-+]+)\*',BOLD+r'\1'+EBOLD,data)
    data = re.sub(r'.*\n',replace_lines,data)
    data = data.replace("\n\n",PARA)
    data = data.replace("\n",LINE)
    ld.write(data)


register_mime('text/plain',process_text)
register_filetype('.txt',process_text)

if __name__ == '__main__':
    ld = LogicalDocument(None)
    process_text(r"""Some text
A paragraph

*Another* parapgraph 3*4 = 12
""",ld)
    print(repr(ld.getvalue()))
