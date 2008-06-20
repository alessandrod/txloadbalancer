README for pythondirector 1.0.0

This is a pure python TCP load balancer. It takes inbound TCP
connections and connects them to one of a number of backend
servers. 

Project home: http://pythondirector.sourceforge.net/
Contact email: Anthony Baxter <anthony@interlink.com.au>

----------------------------------------------------------------------

Features:

  - by default, uses the Twisted framework for async I/O, but can
    also use asyncore.

  - async i/o based, so much less overhead than fork/thread based
    balancers

  - Multiple scheduling algorithms (random, round robin, leastconns,
    leastconns-least-recently-used)

  - If a server fails to answer, it's removed from the pool - the
    client that failed to connect gets transparently failed over to 
    a new host.

  - xml based configuration file

  - seperate management thread that periodically re-adds failed hosts
    if they've come back up.

  - optional builtin webserver for admin

----------------------------------------------------------------------

Performance:

  - On my notebook, load balancing an apache on the same local ethernet
    (serving a static 18K text file) gets 155 connections per second and
    2850 kbytes/s throughput (apachebench -n 2000 -c 10). Connecting directly
    to the apache gets 180 conns/sec and 3400kbytes/s. So unless you're 
    serving really really stupidly high hit rates it's unlikely to be 
    pythondirector causing you difficulties. (Note that 155 connections/sec 
    is 13 million hits per day...)

  - Running purely over the loopback interface to a local apache seems to
    max out at around 350 conns/second.

----------------------------------------------------------------------

API (web based):

    See doc/webapi.txt for a full list of web api commands

----------------------------------------------------------------------

Twisted vs. asyncore

Pythondirector will use either twisted or asyncore for it's networking -
it prefers twisted.  The twisted implementation is much, much faster, 
but does require an additional package - see http://www.twistedmatrix.com 
for the software.

I've also seen "weird failures" from asyncore with some sort of nasty
race condition. 

----------------------------------------------------------------------

Changes from 0.0.7 to 1.0.0

- Very few, mostly this is to update the project to 'stable' status.
- The networking code now uses twisted if available, and falls back
  to asyncore.

Changes from 0.0.6 to 0.0.7

- You can specify a hostname of '*' to the listen directive for both
  the scheduler and the administrative interface to mean 'listen on
  all interfaces'. Considerably more obvious than '0.0.0.0'. Thanks
  to Andrew Sydelko for the idea.
- New "leastconnsrr" scheduler - this is leastconns, with a roundrobin
  as well. Previously, leastconns would keep the list of hosts sorted,
  which often meant one system got beaten up pretty badly.
- Twisted backend group selection works again.
- The client address is now passed to the scheduler's getHost() method. 
  This allows the creation of "sticky" schedulers, where a client is 
  (by preference) sent to the same backend server. The factory function
  for schedulers will change to allow things like "roundrobin,sticky".

Changes from 0.0.5 to 0.0.6:

- fixed an error in the (hopefully rare) case where all backend servers
  are down.
- the main script uses resource.setrlimit() to boost the number of open
  filedescriptors (solaris has stupidly low defaults)
- when all backend servers are down, the manager thread goes into a much
  more aggressive mode re-adding them.
- handle comments in the config file

Changes from 0.0.4 to 0.0.5:

- bunch of bugfixes to the logging
- re-implemented the networking code using the 'twisted' framework
  (a simple loopback test:
    asyncore based pydir:
      Requests per second:    107.72
      Transfer rate:          2462.69 kb/s received
    twisted based pydir:
      Requests per second:    197.90
      Transfer rate:          4519.69 kb/s received
    (5 way, 2000 fetches)
  )

Changes from 0.0.3 to 0.0.4:

- can now specify more than one listener for a service
- 'client' in the config XML is now 'host'
- fixed a bug in leastconns and roundrobin scheduler if all backends
  were unavailable.
- whole lotta documentation added.
- running display in web api now shows count of total connections
- running display now has refresh and auto-refresh
- compareconf module - takes a running config and a new config and
  emits the web api commands needed to make the running config match
  the new config
- first cut at enabling https for web interface (needs m2crypto)

Changes from 0.0.2 to 0.0.3:

- delHost hooked up
- running.xml added - XML dump of current config
- centralised logging - the various things that write logfile 
  entries need to be made consistent, and a lot of additional 
  logging needs to be added.
- Python2.1 compatibility fix: no socket.gaierror exception on 2.1

Changes from 0.0.1 to 0.0.2:

- refactored web publishing (babybobo)
- package-ised and distutil-ised the code

----------------------------------------------------------------------

This software is covered by the following license:

Copyright (c) 2002-2004 ekit.com Inc (http://www.ekit-inc.com/) 
and Anthony Baxter <anthony@interlink.com.au>

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

