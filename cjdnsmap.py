#!/usr/bin/env python
#
# cjdnsmap.py (c) 2012 Gerard Krol
#
# You may redistribute this program and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Todo:
# - Color nodes depending on the number of connections
#

######## SETTINGS ###############
credentialsFromConfig = True   # Whether or not to get cjdns credentials from ~/.cjdnsadmin
nonames = False                 # Should we even bother trying to look up names?
cjdadmin_ip   = "127.0.0.1"	    #
cjdadmin_port = 11234           #
cjdadmin_pass = "insecure_pass" #
filename      = 'map.svg'	    # Picks format based on filename. If it ends in .svg it's an svg, otherwise it's a png
#################################

import re
import socket
import sys
import math
import json
try:
    import httplib2
except:
    print "Requires httplib2, try: "
    print "sudo easy_install httplib2"
    sys.exit()
try:
    import pydot
except:
    print "Requires pydot, try:"
    print "sudo easy_install pydot"
    sys.exit()
try:
    from cjdns import cjdns_connect, cjdns_connectWithAdminInfo
except:
    print "Requires cjdns python module. It should've been included"
    print "with this program. Please ensure that it's in the path. It"
    print "also comes with cjdns, check contrib/python/ in the cjdns source"
    sys.exit()


if len(sys.argv) == 5:
    cjdadmin_ip = sys.argv[1]
    cjdadmin_port = int(sys.argv[2])
    cjdadmin_pass = sys.argv[3]
    filename = sys.argv[4]
    print "Using credentials from argv"
elif len(sys.argv) == 2:
    filename = sys.argv[1]
elif len(sys.argv) != 1:
    print "Usage is:"
    print sys.argv[0] + " <ip> <port> <pass> <filename>"
    print "Or:"
    print sys.argv[0] + " [<filename>]"

#################################################
# code from http://effbot.org/zone/bencode.htm
# Fredrik Lundh 
#
# Unless otherwise noted, source code can be be used freely. Examples, 
# test scripts and other short code fragments can be considered as 
# being in the public domain. Downloads usually include a README file 
# that includes the relevant copyright/license information.

def tokenize(text, match=re.compile("([idel])|(\d+):|(-?\d+)").match):
    i = 0
    while i < len(text):
        m = match(text, i)
        s = m.group(m.lastindex)
        i = m.end()
        if m.lastindex == 2:
            yield "s"
            yield text[i:i+int(s)]
            i = i + int(s)
        else:
            yield s

def decode_item(next, token):
    if token == "i":
        # integer: "i" value "e"
        data = int(next())
        if next() != "e":
            raise ValueError
    elif token == "s":
        # string: "s" value (virtual tokens)
        data = next()
    elif token == "l" or token == "d":
        # container: "l" (or "d") values "e"
        data = []
        tok = next()
        while tok != "e":
            data.append(decode_item(next, tok))
            tok = next()
        if token == "d":
            data = dict(zip(data[0::2], data[1::2]))
    else:
        raise ValueError
    return data

def decode(text):
    try:
        src = tokenize(text)
        data = decode_item(src.next, src.next())
        for token in src: # look for more tokens
            raise SyntaxError("trailing junk")
    except (AttributeError, ValueError, StopIteration):
        raise SyntaxError("syntax error")
    return data

# end code from http://effbot.org/zone/bencode.htm
###################################################

###################################################
def hsv_to_rgb(h,s,v):
    """ convert hsv to rgb. h is 0-360, s and v are 0-1"""
    r = 0.0
    g = 0.0
    b = 0.0
    chroma = v * s
    h_dash = h / 60.0
    x = chroma * (1.0 - math.fabs((h_dash % 2.0) - 1.0))
 
    if h_dash < 1.0:
        r = chroma
        g = x
    elif h_dash < 2.0:
        r = x
        g = chroma
    elif h_dash < 3.0:
        g = chroma
        b = x
    elif h_dash < 4.0:
        g = x
        b = chroma
    elif h_dash < 5.0:
        r = x
        b = chroma
    elif h_dash < 6.0:
        r = chroma
        b = x
 
    m = v - chroma
    r += m
    g += m
    b += m
    return (r,g,b)
    
def hsv_to_color(h,s,v):
    r,g,b = hsv_to_rgb(h,s,v)
    return '#{0:02x}{1:02x}{2:02x}'.format(int(r*255),int(g*255),int(b*255))

###################################################

try:
    cjdns = cjdns_connect(cjdadmin_ip, cjdadmin_port, cjdadmin_pass)
except:
    cjdns = cjdns_connectWithAdminInfo()
    
class route:
    def __init__(self, ip, name, path, link):
        self.ip = ip
        self.name = name
        route = path
        route = route.replace('.','')
        route = route.replace('0','x')
        route = route.replace('1','y')
        route = route.replace('f','1111')
        route = route.replace('e','1110')
        route = route.replace('d','1101')
        route = route.replace('c','1100')
        route = route.replace('b','1011')
        route = route.replace('a','1010')
        route = route.replace('9','1001')
        route = route.replace('8','1000')
        route = route.replace('7','0111')
        route = route.replace('6','0110')
        route = route.replace('5','0101')
        route = route.replace('4','0100')
        route = route.replace('3','0011')
        route = route.replace('2','0010')
        route = route.replace('y','0001')
        route = route.replace('x','0000')
        self.route = route[::-1].rstrip('0')[:-1]
        self.quality = link / 5366870.0 # LINK_STATE_MULTIPLIER
        
    def find_parent(self, routes):
        parents = [(len(other.route),other) for other in routes if self.route.startswith(other.route) and self != other]

        parents.sort(reverse=True)
        if parents:
            parent = parents[0][1]
            return parent
        return None
        
# retrieve the node names from the page maintained by Mikey
page = 'http://[fc5d:baa5:61fc:6ffd:9554:67f0:e290:7535]/nodes/list.json'
print('Downloading the list of node names from {0} ...'.format(page))
names = {}
h = httplib2.Http(".cache")
if not nonames:
    try:
        r, content = h.request(page, "GET")
        nameip = json.loads(content)['nodes']
    except:
        print "Connection to Mikey's nodelist failed, continuing without names"
        nameip = {}
else:
    nameip = {}

existing_names = set()
doubles = set()

for node in nameip:
    if not node['name'] in doubles:
        names[node['ip']]=node['name']
    else:
        names[node['ip']]=node['name'] + ' ' + ip.split(':')[-1]

"""
page = 'http://ircerr.bt-chat.com/cjdns/ipv6-cjdnet.data.txt'
print('Downloading the list of node names from {0} ...'.format(page))
names = {}
h = httplib2.Http(".cache")
r, content = h.request(page, "GET")

existing_names = set()
doubles = set()
nameip = []
for l in content.split('\n'):
    l = l.strip()
    if not l or l.startswith('#'):
        continue
    d = l.split(' ')
    if len(d) < 2:
        continue # use the standard last two bytes
    ip   = d[0]
    name = d[1]
    nameip.append((name,ip))
    if name in existing_names:
        doubles.add(name)
    existing_names.add(name)
    
for name,ip in nameip:
    if not name in doubles:
        names[ip]=name
    else:
        names[ip]=name + ' ' + ip.split(':')[-1]
"""

routes = [];
i = 0;
while True:
    table = cjdns.NodeStore_dumpTable(i)
    for r in table['routingTable']:
        name = r['ip'].split(':')[-1]
        if r['ip'] in names:
            name = names[r['ip']]
        routes.append(route(r['ip'],name,r['path'],r['link']))
    if not 'more' in table:
        break
    i += 1

        
# sort the routes on quality
tmp = [(r.quality,r) for r in routes]
tmp.sort(reverse=True)
routes = [q[1] for q in tmp]

family_set = set()
family_list = []
class MyNode:
    def __init__(self, name):
        self.name = name
        self.connections = 0
        self.active_connections = 0
        p = self.name.split('.')
        if len(p) == 1:
            self.family = None
        else:
            self.family = '.'.join(p[1::])
            if not self.family in family_set:
                family_set.add(self.family)
                family_list.append(self.family)
    def Node(self):
        if self.active_connections:
            color = 'black'
            if self.name in existing_names:
                fontcolor = 'black'
            else:
                fontcolor = 'black'
            if not self.family:
                fillcolor = 'white'
            else:
                h = family_hues[self.family]
                s = 0.3
                v = 1.0
                fillcolor = hsv_to_color(h,s,v)
        else:
            if not self.family:
                h = 0.0
                s = 0.0
                v = 0.6
            else:
                h = family_hues[self.family]
                s = 0.5
                v = 0.7
            color = hsv_to_color(h,s,v)
            fontcolor = color
            fillcolor = 'white'
        self.node = pydot.Node(self.name, shape='box', color=color, fontcolor=fontcolor, style='filled', fillcolor=fillcolor)
        return self.node
        
family_hues = {}
def calculate_family_hues():
    family_list.sort() # so they get the same color every time
    for i,f in enumerate(family_list):
        family_hues[f] = 360.0/len(family_list)*i

nodes = {}
for r in routes:
    if not r.ip in nodes:
        nodes[r.ip] = MyNode(r.name)

# we need to find the parents for every node and draw a line
# to do this we take the route and find the node with the longest
# overlap at the end
# we then assume this is the parent

link_strength = {}
def linked(a,b):
    a,b = sorted([a,b])
    return (a,b) in link_strength
def set_link_strength(a,b,s):
    a,b = sorted([a,b])
    if not linked(a,b):
        link_strength[(a,b)] = s
    else:
        l = link_strength[(a,b)]
        if s > l:
            link_strength[(a,b)] = s

edges = []
def add_edges(active,color):
    for r in routes:
        if active and r.quality == 0:
            continue
        if not active and r.quality > 0:
            continue
        parent = r.find_parent(routes)
        if parent:
            pn = nodes[parent.ip]
            rn = nodes[r.ip]
            if not linked(pn,rn):
                pn.connections += 1
                rn.connections += 1
                if active:
                    weight = '1'
                    pn.active_connections += 1
                    rn.active_connections += 1
                else:
                    weight = '0.01'
                edges.append((pn,rn,weight,color,r.quality))
            set_link_strength(pn,rn,r.quality)
add_edges(True,'black')
add_edges(False,'grey')

graph = pydot.Dot(graph_type='graph', K='2', splines='true', dpi='50', maxiter='10000', ranksep='2', nodesep='1', epsilon='0.1', overlap='false')
calculate_family_hues()
for n in nodes.itervalues():
    graph.add_node(n.Node())
for pn,rn,weight,color,quality in edges:
    width = math.log(float(quality)+1)
    if width < 1:
        width = 1
    style = 'setlinewidth({0})'.format(width)
    len = '0.5'
    minlen = '0.5'
    if quality > 0:
        len = str(6/width)
    if pn.connections == 1 or rn.connections == 1:
        weight = '1'
    edge = pydot.Edge(pn.node,rn.node, color=color, len=len, weight=weight, minlen=minlen, style=style)
    graph.add_edge(edge)

print('Generating the map...')
if filename.split(".")[-1] == "svg":
    graph.write_svg(filename, prog='fdp')
else:
    graph.write_png(filename, prog='fdp')
print('Map written to {0}'.format(filename))
