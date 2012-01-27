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

import pydot
import re
import socket
import httplib2
import sys

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
        self.quality = link
        
    def find_parent(self, routes):
        parents = [(len(other.route),other) for other in routes if self.route.startswith(other.route) and self != other]

        parents.sort(reverse=True)
        if parents:
            parent = parents[0][1]
            return parent
        return None
        
if len(sys.argv) > 1:
    filename = sys.argv[-1]
else:
    filename = 'map.png'
        
# retrieve the node names from the page maintained by ircerr
names = {}
h = httplib2.Http(".cache")
r, content = h.request('http://[fc38:4c2c:1a8f:3981:f2e7:c2b9:6870:6e84]/ipv6-cjdnet.data.txt', "GET")

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

# retrieve the routing data from the admin interface
# FIXME: read these from the commandline or even from the config

HOST = 'localhost'
PORT = 11234
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.send('d1:q19:NodeStore_dumpTable4:txid4:....e')
data = ''
while True:
    r = s.recv(1024)
    data += r
    if not r or r.endswith('....e\n'):
        break
s.close()
data = data.strip()
bencode = decode(data)

routes = []
for r in bencode['routingTable']:
    ip = r['ip']
    path = r['path']
    link = r['link']
    if ip in names:
        name = names[ip]
    else:
        name = ip.split(':')[-1]
    r = route(ip,name,path,link)
    routes.append(r)
        
# sort the routes on quality
tmp = [(r.quality,r) for r in routes]
tmp.sort(reverse=True)
routes = [q[1] for q in tmp]

class MyNode:
    def __init__(self, name):
        self.name = name
        self.connections = 0
        self.node = pydot.Node(name, shape='box')

nodes = {}
for r in routes:
    if not r.ip in nodes:
        nodes[r.ip] = MyNode(r.name)

# we need to find the parents for every node and draw a line
# to do this we take the route and find the node with the longest
# overlap at the end
# we then assume this is the parent

already_linked = set()
def linked(a,b):
    if a == b:
        return True
    return (a,b) in already_linked
def set_linked(a,b):
    already_linked.add((a,b))
    already_linked.add((b,a))

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
                if active:
                    pn.connections += 1
                    rn.connections += 1
                    weight = '0.05'
                else:
                    weight = '0'
                edge = pydot.Edge(pn.node,rn.node, color=color, len='6', weight=weight, minlen='4')
                edges.append(edge)
                set_linked(pn,rn)
add_edges(True,'black')
add_edges(False,'grey')

graph = pydot.Dot(graph_type='graph', K='0.25', splines='true', dpi='60', maxiter='10000', ranksep='0', nodesep='0', epsilon='0.01', concentrate='true')
for n in nodes.itervalues():
    graph.add_node(n.node)
for edge in edges:
    graph.add_edge(edge)

    
graph.write_png(filename, prog='fdp') # dot neato twopi fdp circo
print('map written to {0}'.format(filename))
