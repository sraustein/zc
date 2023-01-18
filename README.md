zc zone compiler
================

## Overview ##

This is a small tool for generating DNS zones from relatively
simple text files, with some automation to handle complex or
repetitive tasks and to automate generation of reverse zone data.

`zc` ("zone compiler") is a Python script which uses an external
package (Bob Halley's excellent [dnspython][] toolkit) to do a lot of
the the heavy lifting.

`zc` can be used either as a straightforward command line tool or as a
pair of `pre-receive` and `post-receive` hooks in a bare git
repository.  In the latter mode, `zc` pulls its input data and
configuration directly from commits pushed to the master branch in the
git repository, using another external library ([GitPython][]).

Upshot of all this is that, once the git repository has been set up,
you just clone a copy of the repository, edit flat text files with
your favorite editor, commit and push, and you're done.  Compilation
will happen automatically when you push, any serious errors will abort
the push so you can fix them and try again, and output will be
installed automatically if there were no serious errors.


## Installation ##

`zc` is perfectly happy to run directly out of a clone of this source
code repository, but you can also install it using the usual tools:

### Python setuptools ###

You can install `zc` using the included `setup.py` in the usual
fashion:

```
python setup.py build
python setup.py install
```

The `setuptools` installation command takes a number of options
controlling things like whether you're installing to the base system
location, to a shared add-on location like `/usr/local/`, or to a
user-specific location.  Run `python setup.py install --help` for
details.

### Debian packaging ###

The source repository includes a basic Debian package setup for use on
Debian, Ubuntu, and related systems.  Building Debian packages is a
complex topic beyond the scope of this document, but if you have the
usual tools installed, something like this should work:

```
pdebuild --buildresult ..
debi --with-depends
```

You can of course also load the package into an APT repository,
install it directly with `dpkg -i`, whatever amuses you.

### Dependencies ###

As mentioned above, `zc` depends on `dnspython` and `GitPython`.  Both
of the packaging methods declare these dependencies in their
respective packaging structure, but you can also install the
dependencies directly if neceessary (eg, if running `zc` itself out of
its source tree).

setuptools:
```
pip install dnspython
pip install GitPython
```

Debian:
```
apt-get install python-dnspython python-git
```


## Command line use ##

If you just want to use `zc` as a command line tool, it's simple.
Usage as of this writing (subject to change, run `zc --help` for
current syntax):

    usage: zc [-h] [-o OUTPUT_DIRECTORY] [-l {debug,info,warning,error}]
	      input [input ...]

    Generate zone files from a simpl(er) flat text file.

    General intent here is to let users specify normal hosts in a simple
    and compact format, with a few utilities we provide to automate
    complex or repetitive stuff, including automatic generation of AAAA
    RRs based on a mapping scheme from A RRs.

    After generating the text of the forward zone, we run it through
    dnspython's zone parser, then generate reverse zones by translating
    the A and AAAA RRs in the forward zone into the corresponding PTR RRs.

    positional arguments:
      input                 input file

    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
			    directory for output files (default: .)
      -l {debug,info,warning,error}, --log-level {debug,info,warning,error}
			    how loudly to bark (default: warning)

You can supply more than one input file, `zc` will process them all
together before writing out any of the zone files.


## Use as git hooks ##

The following discussion assumes that you're keeping your `zc` input
files in a git repository.  We are *not* talking about the `zc` source
repository here: data files should be a *separate* bare git
repository.  You can put anything you like in that repository so long
as it obeys the rules below, but in most cases you will just want a
`config.json` file, one or more `zc` input files, and perhaps a README
explaining usage details and local conventions.

You'll want to create this repository on the server system where you
run the DNS name server which will be primary for the zone(s) you
administer with `zc`, so that it can install its output directly to
the name server.  If putting something like this on one of your public
name servers sounds scary, you can set `zc` up on a separate server
and run that as a stealth primary, with your public name servers as
secondaries (for the relevant zone(s)) of the stealth primary.

In most cases you'll want to set up a separate userid (`zc`, by
convention, but use whatever you like) to own the bare git repository,
so that you can set it up with a locked-down ssh configuration to
restrict git access to people authorized to change the zone.  The `zc`
package includes an auxiliary program `git-remote-only` suitable for
use in `~zc/.ssh/authorized_keys`.

To create a suitable userid and bare repository on Linux, you might do
something like this:

```
sudo adduser --disabled-password --gecos 'ZC user' zc
sudo git init --bare ~zc/dns.git
sudo mkdir ~zc/.ssh
sudo chown -R root:root ~zc
sudo chown -R zc:zc ~zc/dns.git
sudo ln -s /usr/bin/zc ~zc/dns.git/hooks/pre-receive
sudo ln -s /usr/bin/zc ~zc/dns.git/hooks/post-receive
```

You'll need to populate `~zc/.ssh/authorized_keys` to set up keys for
users who are allowed to use this repository.
`~zc/.ssh/authorized_keys` must be *readable* by user `zc`, but need
not be writable by user `zc`, so the ssh configuration can be owned by
root, and since it only contains public keys there's no particular
harm in making it world readable.  See comments in `git-remote-only`
for details on how to use that script.

When used as git hooks, configuration can't come from the command
line, so it comes from two places:

1. A file called `config.json` in the repository, and

2. Variables set in the configuration of the bare git repository where
   the `pre-receive` and `post-receive` hooks are installed.

The general idea is that stuff which should be under control of the
data owner is controlled by `config.json`, while stuff that should be
controlled by the server operator is controlled by configuration
variables in the server git repository.  These are described below.

We want to make sure that the zones compile correctly *before*
allowing the `git push` operation to complete, then, assuming
everything's OK, we want to install the zones *after* the commit
completes.

All the real work happens in the `pre-receive` hook, the
`post-receive` hook's job is just to trigger final installation of the
output zone files after `git-receive-pack` finishes accepting the
push.  If you don't understand git well enough to know what that
means, don't worry about it.  If you want to learn more, see
[githooks][], but the learning curve necessary for the documentation
to make any sense is a bit steep, so bring a bag lunch.

`zc` determines whether it's running as one of the git hooks or not by
examining the name by which it was invoked: if the name ends with
`/pre-receive` or `/post-receive`, it's a hook, otherwise you get the
command line behavior.  In practice, this means that you can just
install `zc`, symlink the correct hook names to whereever you
installed the `zc` script, and the right thing should happen.


### `config.json` settings ###

The list of input files and the verbosity are set in the JSON file,
while the output directory is set in the git configuration on the
server where the bare git repository lives.

    {
        "zones": ["foo.zone", "bar.zone"],
        "log-level": "info"
    }

The `zones` parameter is mandatory, and specifies the names of the
input files within the git repository (at the moment we only look at
the top-level directory -- we could change this given a reason).

The `log-level` parameter is optional, and defaults to `warning`.


### git server repository settings ###

All of the following settings have defaults except for `zc.output-directory`.

    git --git-dir /where/ever.git config zc.output-directory /my/output/directory

The `zc.output-directory` parameter in the git repository's
configuration file specifies the location of the directory to which
`zc` should write its final output.  `zc` also uses this directory to
stash a FIFO which it uses to coordinate actions between the
`pre-receive` and `post-receive` hooks.

There is no default for `zc.output-directory`, you must set it.

    git --git-dir /where/ever.git config zc.hook-timeout 15

`zc.hook-timeout` controls how many seconds the `pre-receive` hook
should wait for confirmation from the `post-receive` hook before
giving up.  The default value of 15 seconds should be fine unless your
server is really slow.

    git --git-dir /where/ever.git config zc.post-command 'rndc reload'

`zc.post-command`, if set, specifies a command to run after all
generated files have been installed.  The default is not to run any
such command.

    git --git-dir /where/ever.git config zc.log-file  /var/log/zc/zc.log
    git --git-dir /where/ever.git config zc.log-level warning
    git --git-dir /where/ever.git config zc.log-file-hours 24
    git --git-dir /where/ever.git config zc.log-file-count 7

When running in git hook mode, `zc` can log to both `stderr` (which
git passes back to the user executing the push) and to a log file.
The `zc.log-*` parameters control the log file.

`zc.log-file` is the name of the log file; if not set, `zc` will not
log to a file.

`zc.log-level` is optional, and defaults to `warning`.

`zc.log-file-hours` controls how many hours should elapse before `zc`
rotates its log file.  The default is 24 hours.

`zc.log-file-count` controls how many old log files `zc` should keep.
The default is 7.


## Zone generation ##

Other than `config.json`, the input files to `zc` look the same
regardless of whether you're running `zc` on the command line or via
git hooks.

While `zc` generates both forward and reverse zones, the underlying
mechanisms are (deliberately) very different, so it's simplest to
consider them separately.  Forward zones are driven from human-edited
files, while reverse zones are generated completely automatically from
the corresponding forward zones.


### Forward zone generation ###

Forward zone generation starts with a flat text file which is parsed
line-by-line to produce a forward zone file.  There three basic kinds
of lines in this file:

1. Stuff passed unchanged through `zc`: blank lines, comments, raw DNS
   RRs (for things other than addresses), and standard control
   operations like $TTL and $ORIGIN.

2. Name-address pairs, processed to generate A and AAAA RRs.

3. Control operations, all of which have names starting with "$".

`zc` requires that the text file start with a `$ORIGIN` control to
specify the name of the zone itself.

Other than the above, the one bit of processing `zc` performs is
replacement of the string "@SERIAL@ in an SOA RR with a
seconds-since-epoch integer timestamp.


#### Name-address pairs ####

"Name-address pairs" are exactly what they sound like: something that
a DNS zone file parser would consider a valid owner name, and and an
IP address (IPv4 or IPv6).

Processing of one name-address pair produces either one or two RRs,
depending on whether automatic generation of IPv6 addresses from IPv4
addresses is enabled when `zc` processes this name-address pair (see
the `$MAP` control operation, below).

Example:

    $MAP yes

    ; A couple of dual-stack hosts, with IPv6 addresses generated
    ; algorithmically from the IPv4 addresses.

    tweedledee          10.0.0.1
    tweedledum          10.0.0.2

    $MAP no

    ; Three single-stack hosts, addresses are what you see, RR type
    ; inferred from the address family

    larry               10.0.0.3
    moe                 2002:a00::4
    curly               10.0.0.5


#### `$MAP` and `$MAP_RULE` ####

The `$MAP` control operation enables or disables automatic generation
of IPv6 addresses from IPv4 addresses, according to zone-specific
mappings specified by the `$MAP_RULE` operation.

`$MAP` is simple: it takes one argument, `yes` or `no` (`on`,
`off`, `true`, and `false` are allowed as aliases).

`$MAP_RULE` takes two arguments: a prefix and a format string.  You
can specify `$MAP_RULE` more than once to build up an ordered set of
mapping rules.  When mapping is enabled, a given address will be
checked against the prefix of each rule in turn: the format string
from the first matching rule (if any) will be used to format the
mapped address.

Format strings are in the syntax used by Python's `str.format()`
operator; the `.format()` operator will be called with one argument,
the input address converted to a tuple of integers, one per byte in
the binary representation of the input address.  So an input address
of `10.0.0.44` would be yield the tuple `(10, 0, 0, 44)`, and so forth.

    $MAP_RULE   10.1.3.0/24             2002:a00:0000:f{0[2]}::{0[3]}
    $MAP_RULE   10.1.0.0/16             2002:a00:0000:{0[2]}::{0[3]}

    $MAP on

    larry       10.1.2.3
    moe         10.1.3.2

    $MAP off

    curly       10.1.4.1

This mechanism is intended primarily for mapping IPv4 addresses to
IPv6 addresses.  The mechanism itself is address-family-agnostic: in
principal, it should work equally well in the other direction if you
can specify a useful set of rules, but the author has not tested this.


#### `$RANGE` ####

The `$RANGE` control operation is a variation on the same general idea
as the (BIND9-specific) `$GENERATE` control operation, but is, in the
author's opinion, a bit easier both to use and to read.  For all but
the most esoteric uses, it takes three or four arguments:

1. A format string to generate the name field of the resulting RRs.

2. A start addresses (IPv4 or IPv6).

3. A stop address

4. An optional numeric `offset`.

The basic idea here is to generate a sequence of A or AAAA RRs (type
selected automatically to fit the addresses provided) for every
address in the specified range, inclusive, with names generated
according to a format string containing a numeric field.

An `offset` value of zero would start with the name generated by
applying the format string to the number zero; an `offset` value of
one would start with the name generated by applying the format string
to the number 1, and so forth.  If the `offset` field isn't specified
at all, it defaults to the numeric value of the least significant
octet of the start address.

Examples:

    ; Access points using $RANGE. This is equivalent to:
    ;
    ;  ap-101           10.0.1.101
    ;  ap-102           10.0.1.102
    ;  ...
    ;  ap-200           10.0.1.200

    $RANGE      ap-{:d} 10.0.1.101 10.0.1.200

    ; Switches, also using $RANGE, but with the numeric input to the
    ; format string explicitly specified rather than inferred from the
    ; IPv4 addressing.  Equivalent to:
    ;
    ; sw-1              10.0.3.17
    ; sw-2              10.0.3.18
    ; ...
    ; sw-26             10.0.3.42

    $RANGE      sw-{:d} 10.0.3.17 10.0.3.42 1

    ; Finally, a whole lot of DHCP client addresses, for IPv4
    ; addresses ranging from  10.1.0.50 to 10.2.255.254, names left as
    ; an exercise for the reader.

    $RANGE dhcp-f{:03x} 10.1.0.50 10.2.255.254 50


#### `$INCLUDE` ####

`$INCLUDE` is a standard control operator, but for the main expected
`zc` use cases there's not much need for it.

`zc` supports a limited form of the `$INCLUDE` operator, intended
mainly for automation (that is, for cases where one wants to include a
machine-generated set of DNS data into a larger zone that you're
maintaining with `zc`).  Limitations:

1. `zc` doesn't support the optional `origin` field of the `$INCLUDE`
   operator as defined in RFC 1035.

2. `zc` does *not* preserve the current `$ORIGIN` value of the outer
   file while processing `$INCLUDE`, so if the included file changes
   the `$ORIGIN`, the outer file will see that change.  Don't do that.

#### `$GENERATE` ####

The `$GENERATE` control operators is not currently implemented.

`$GENERATE` is a BIND-specific control operator.  We could implement
it if there were a real need, but the `$RANGE` operator covers the
things for which we have been using `$GENERATE` in the forward zone.

Our current use of `$GENERATE` in reverse zones is a source of
consistency problems, and is therefore unsupported with prejudice.


#### `$REVERSE_ZONE` ####

The `$REVERSE_ZONE` control operation has no effect on the forward
zone.  Rather, it's a mechanism for specifying the list of reverse
zones which should be generated from this forward zone.  We include
this in the input source for the forward zone in order to keep all the
data describing the zone in one place.

If you don't use the `$REVERSE_ZONE` control, `zc` will not generate
any reverse data for this forward zone.

Sample:

    $REVERSE_ZONE 0.10.in-addr.arpa
    $REVERSE_ZONE 1.10.in-addr.arpa
    $REVERSE_ZONE 2.10.in-addr.arpa
    $REVERSE_ZONE 0.0.0.0.0.0.a.0.2.0.0.2.ip6.arpa


### Reverse zone generation ###

As noted above, reverse zones are generated entirely from data
extracted from the forward zone.  This is deliberate: we are trying to
make sure that the reverse data corresponds to the forward data, and
giving the user an opportunity to get creative here is just asking for
trouble.

The basic strategy is:

* Create a reverse zone object for every name listed in the forward
  zone's source via `$REVERSE_ZONE` operators.

* For each `A` and `AAAA` RR in the forward zone, generate the
  corresponding `PTR` RR and and find the reverse zone in which that
  RR belongs; whine for each PTR RR that doesn't fit into any
  specified reverse zone.

* Populate the zone apex data (SOA and apex NS RRsets) of each reverse
  zone by copying the corresponding rdata from the forward zone.  Yes,
  this assumes that the forward and reverse zones are served by the
  same servers; we could "fix" that given a need, but as of this
  writing no such need exists, and this keeps it simple.


## Copyright ##

Copyright (c) 2017-2019, Grunchweather Associates

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.


[dnspython]:    http://www.dnspython.org
[GitPython]:	https://github.com/gitpython-developers/GitPython
[githooks]:     https://git-scm.com/docs/githooks
