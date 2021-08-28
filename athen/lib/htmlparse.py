from registry import *
import bs4             # BeautifulSoup 4

    
def _worker(node,ld):
    if type(node) is bs4.Tag:
        if node.name == 'a':
            ld.write(HREF+node['href']+MHREF)
            for i in node.children: _worker(i,ld)
            ld.write(EHREF)
        elif node.name == 'b':
            ld.write(BOLD)
            for i in node.children: _worker(i,ld)
            ld.write(EBOLD)
        elif node.name == 'i': # map italic to bold as a general "emphasis" concept
            ld.write(BOLD)
            for i in node.children: _worker(i,ld)
            ld.write(EBOLD)
        elif node.name == 'u':
            ld.write(UND)
            for i in node.children: _worker(i,ld)
            ld.write(EUND)
        elif node.name == 'h1':
            ld.write(HDR1)
            for i in node.children: _worker(i,ld)
            ld.write(EHDR1)
        elif node.name == 'h2':
            ld.write(HDR2)
            for i in node.children: _worker(i,ld)
            ld.write(EHDR2)
        elif node.name == 'h3':
            ld.write(HDR3)
            for i in node.children: _worker(i,ld)
            ld.write(EHDR3)
        elif node.name == 'p':
            for i in node.children: _worker(i,ld)
            ld.write(PARA)
        elif node.name == 'br':
            for i in node.children: _worker(i,ld)
            ld.write(LINE)
        elif node.name in ['style','script','object']:
            pass # don't descend at all
        else:
            # don't print the tag but do descend into its contents
            for i in node.children: _worker(i,ld)
    elif type(node) is bs4.NavigableString:
        s = str(node)
        for i in ["\t","\r","\n"]: s = s.replace(i,"")
        s = s.strip()
        if s: # don't print a string reduced to nothing
            ld.write(s)
    elif hasattr(node,"children"):
        # some other weird type, but we can descend
        for i in node.children: _worker(i,ld)

def process_html(data,ld):
    root = bs4.BeautifulSoup(data)
    _worker(root,ld)


register_mime('text/html',process_html)
register_filetype('.html',process_html)
register_filetype('.htm',process_html)

if __name__ == '__main__':
    pudb.set_trace()
    ld = LogicalDocument()
    process_html(r"""
<html>
<style>Some werid style data</style>
<body>
<p>This is a text with <b>bold</b></P>
<h2>A header</h2>
<p>Some more <br/> text</p>
<p><A HREF="/foo" stupidheader="burble">A link</A></p>
</body>
""",ld)
    print(repr(ld.getvalue()))
