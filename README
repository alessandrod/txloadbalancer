============
Introduction
============

This is a pure python TCP load balancer. It takes inbound TCP connections and
connects them to one of a number of backend servers.

txLoadBalancer is a fork of Anthony Baxter's PythonDirector. It replaced all
threading, asyncore, and admin UI code with the Twisted-based analogs. It also
significantly reorganized the API and provided many new features.


========
Features
========

* It is a pure-Twisted TCP loadbalancer.

* Thanks to Twisted, it's async i/o based, so much less overhead than
  fork/thread based balancers.

* It has multiple scheduling algorithms (random, round robin, leastconns,
  weighted). If a server fails to answer, it's removed from the pool - the
  client that failed to connect gets transparently failed over to a new host.

* Provides an optional builtin webserver for a built-in admin UI.

* Seperate management timer services that perform such tasks as periodically
  readding failed hosts to the rotation, updated on-disk config files with
  changes made to the running server.

* A built-in SSH server for managing (and modifying) a running load-balancer
  instance.

* A Twisted API for adding a load-balancing service to your Twisted application
  without the need to run a separate load-balancer.

* The application uses an XML-based configuration file.
