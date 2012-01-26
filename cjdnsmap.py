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
import requests
import re

#################################################
# code from http://effbot.org/zone/bencode.htm
#
# Copyright © 1995-2010 by Fredrik Lundh 
#
# By obtaining, using, and/ or copying this software and/or its 
# associated documentation, you agree that you have read, understood, 
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and its
# associated documentation for any purpose and without fee is hereby 
# granted, provided that the above copyright notice appears in all 
# copies, and that both that copyright notice and this permission 
# notice appear in supporting documentation, and that the name of 
# Secret Labs AB or the author not be used in advertising or publicity 
# pertaining to distribution of the software without specific, written 
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO
# THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY 
# AND FITNESS. IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE
# FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES 
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

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

names = {
    'fc37:8636:7dea:7f3d:6514:ce73:0f7b:f29d': 'gerard_',
    'fcd9:6fcc:642c:c70d:5ff2:63c3:8ead:c9ad': 'cjd France',
    'fc38:4c2c:1a8f:3981:f2e7:c2b9:6870:6e84': 'sql.btc [hub]',
    'fc9d:2ef7:3fb4:70e1:847c:d810:d5e3:fe21': 'web.btc [hub]',
    'fc37:acb2:544b:ed86:8b8d:9945:add7:b119': 'web2.btc [hub]',
    'fc6c:32ab:968b:0272:ab3c:ad1f:94bd:538e': 'windowlappie.iR [hub]',
    'fca0:e44d:c4ae:8ff8:dafc:5558:4688:35f5': 'backtrack-lappie.iR',
    'fc88:7c4e:8b9a:944d:5ebb:9a46:f67c:e387': 'backtrack-pc.iR',
    'fcae:070a:2a64:5293:f191:6386:fc33:eb4c': 'xubuntu.iR',
    'fcf7:75f0:82e3:327c:7112:b9ab:d1f9:bbbe': 'fileserv.iR',
    'fcae:99fd:1524:e7f7:fcfa:9c6d:db2a:eb31': 'bagga',
    'fce5:de17:cbde:c87b:5289:0556:8b83:c9c8': 'node.c (httpd)',
    'fcf1:a7a8:8ec0:589b:c64c:cc95:1ced:3679': 'kvm.c (pings)',
    'fcec:0cbd:3c03:1a2a:063f:c917:b1db:1695': 'napier (ircd)',
    'fc3a:2804:615a:b34f:abfe:c7d5:65d6:f50c': 'derp (httpd)', # West coast
    'fcd7:61f9:7bd0:4060:851e:1ba9:471f:7f52': 'slw',
    'fc13:6176:aaca:8c7f:9f55:924f:26b3:4b14': 'DIASPORA *ALPHA',
    'fc5d:baa5:61fc:6ffd:9554:67f0:e290:7535': 'Mikey_2', # Detroit
    }

class route:
    def __init__(self, ip, path, link):
        self.ip = ip
        if self.ip in names:
            self.name = names[self.ip]
        else:
            self.name = self.ip.split(':')[-1]
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
        print self.name, self.route
        self.quality = link
        print self.quality
        
    def find_parent(self, routes):
        parents = [(len(other.route),other) for other in routes if self.route.startswith(other.route) and self != other]

        parents.sort(reverse=True)
        if parents:
            parent = parents[0][1]
            print self.name,'has as parent',parent.name, self.route,parent.route
            return parent
        print 'no parent found for',self.name
        return None
        
import socket

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
print bencode

routes = []
for r in bencode['routingTable']:
    r = route(r['ip'],r['path'],r['link'])
    routes.append(r)
        
# sort the routes on quality
tmp = [(r.quality,r) for r in routes]
tmp.sort(reverse=True)
routes = [q[1] for q in tmp]

nodes = {}
for r in routes:
    print r.name,r.quality
    if not r.ip in nodes:
        nodes[r.ip] = pydot.Node(r.name)

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


graph = pydot.Dot(graph_type='graph')
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
                edge = pydot.Edge(pn,rn, color=color)
                graph.add_edge(edge)
                set_linked(pn,rn)
add_edges(True,'black')
add_edges(False,'grey')
    
graph.write_png('map.png', prog='dot') # dot neato twopi
