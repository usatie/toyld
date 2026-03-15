#!/usr/bin/perl
# -*- perl -*-
# $Header: /home/johnl/book/linker/code/RCS/linkproj03.pl,v 1.2 2001/05/01 05:01:57 johnl Exp $
# Project code for Linkers and Loaders by John R. Levine,
# published by Morgan-Kauffman in October 1999, ISBN 1-55860-496-0.
#
# This code is copyright 2001, John R. Levine. Permission is granted
# to individuals to use this code for non-commercial purposes in
# unmodified or modified form.  Permission is also granted to
# educational institutions to use this code for educational purposes
# in unmodified or modified form.  Other uses, such as including it
# in a product or service offered for sale, require permission from
# the author. 

# Project 3-1: read and write object files

require 'readobj.pl';

$inf = shift || die "need a file name";

%obj = %{readobject($inf)};
writeobject("newobj", \%obj);
