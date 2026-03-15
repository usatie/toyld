#!/usr/bin/perl
# -*- perl -*-
# $Header: /home/johnl/book/linker/code/RCS/linkproj04-2.pl,v 1.2 2001/07/23 05:07:49 johnl Exp $
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

# Project 4-2: Unix style storage allocation with the common block hack

use integer;

require 'readobj.pl';

# some parameters

$textbase = 0x1000;		# where the text starts
$pagealign = 0x1000;		# round up for data
$wordalign = 0x4;		# round up for bss and concat'ed segments

# round up a value to a 
sub roundup($$) {
    my ($value, $roundval) = @_;

    return ($value+$roundval-1) & -$roundval;
}

# first read in all of the object files

foreach $fn (@ARGV) {
    push @objects, readobject($fn);
}

# now collect the total sizes of each segment

$tsize = $dsize = $bsize = 0;

foreach $o (@objects) {
    print "visit $o->{name}, ";
    my $t = $o->{segs}[$o->{segnames}->{".text"}];
    $tsize += roundup($t->{size}, $wordalign) if $t;

    my $d = $o->{segs}[$o->{segnames}->{".data"}];

    $dsize += roundup($d->{size}, $wordalign) if $d;

    my $b = $o->{segs}[$o->{segnames}->{".bss"}];

    $bsize += roundup($b->{size}, $wordalign) if $b;
    printf "%X %X %X\n", $tsize, $dsize, $bsize;
}

# set the base of each segment

$tbase = $textbase;

$dbase = roundup($tbase+$tsize, $pagealign); # data is page aligned

$bbase = roundup ($dbase+$dsize, $wordalign); # bss is word aligned

printf "base %X %X %X\n", $tbase, $dbase, $bbase;

# now create enough symbol table to find the common blocks 

%sym = ();			# the symbol table

foreach $o (@objects) {
    foreach $s (@{$o->{syms}}) {
	next unless $s;		# skip null 0th entry

	my $sn = $s->{name};
	my $st = $s->{type};

	my $sy = $sym{$sn};	# existing symbol

	if($sy) {
	    if($st eq "D") {
		if($sy->{type} eq "D") {
		    print "Multiply defined $sn\n";
		} else {
		    $sy = $s;
		    $sy->{source} = $o;
		    $sym{$sn} = $sy;
		    next;
		}
	    } elsif($st eq "U" and $sy->{type} eq "U") {
		next if $sy->{value} >= $s->{value};
	    }
	}
	# use this  value
	$sym{$sn}->{value} = $s->{value};
	$sym{$sn}->{type} = $st;
    }
}

# now set the new base values for each module

# running current base for each segment
$tcbase = $tbase; $dcbase = $dbase; $bcbase = $bbase;

foreach $o (@objects) {
    print "revisit $o->{name}, ";
    my $t = $o->{segs}[$o->{segnames}->{".text"}];
   
    if($t) {
	$t->{oldbase} = $t->{base};
	$t->{base} = $tcbase;

	$tcbase += roundup($t->{size}, $wordalign);
    }

    my $d = $o->{segs}[$o->{segnames}->{".data"}];

    if($d) {
	$d->{oldbase} = $d->{base};
	$d->{base} = $dcbase;

	$dcbase += roundup($d->{size}, $wordalign);
    }

    my $b = $o->{segs}[$o->{segnames}->{".bss"}];

    if($b) {
	$b->{oldbase} = $b->{base};
	$b->{base} = $bcbase;

	$bcbase += roundup($b->{size}, $wordalign);
    }

    printf "%X %X %X\n", $tcbase, $dcbase, $bcbase;
}

$cbase = roundup ($bcbase+$bsize, $wordalign); # bss is word aligned

# now find the commons
while (($n, $s) = each %sym) {
    next unless $s->{type} eq "U";

    my $v = $s->{value};

    if($v == 0) {
	print "Undefined $n\n";
    } else {
	$s->{type} = "D";
	$s->{value} = $cbase;
	# will have to note it's in BSS sometime
	$cbase = roundup ($cbase+$v, $wordalign); # bss is word aligned
	printf "Common $n size $v, location %X\n", $s->{value};
    }
}

# now create the output object

%out = (
    name => "a.out.lk",
    nseg => 3,
    nsym => 0,
    nrel => 0,
    segnames => {
	".text" => 1,
	".data" => 2,
	".bss" => 3
	},
    segs => [
	     undef,
	     {
		 name => ".text",
		 segno => 1,
		 base => $tbase,
		 size => $tsize,
		 flags => "RP",
	     },
	     {
		 name => ".data",
		 segno => 2,
		 base => $dbase,
		 size => $dsize,
		 flags => "RWP",
	     },
	     {
		 name => ".bss",
		 segno => 3,
		 base => $bbase,
		 size => $bsize,
		 flags => "RW",
	     }
	     ]
);

writeobject($out{name}, \%out);
