#!/usr/bin/perl
# -*- perl -*-
# $Header: /home/johnl/book/linker/code/RCS/linkproj04-3.pl,v 1.1 2001/07/23 05:07:29 johnl Exp $
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

# Project 4-3: Unix style storage allocation with arbitrary segments

use integer;

require 'readobj.pl';

# some parameters

$textbase = 0x1000;		# where the text starts
$pagealign = 0x1000;		# round up for data
$wordalign = 0x4;		# round up for bss and concat'ed segments

# segment groups

# arrays listing segments in order
@textgroup = (".text");
@datagroup = (".data");
@bssgroup = (".bss");

# hash of which segment is in which group
# and the total size and which objects have it

%groups = (".text" => { group => \@textgroup, size => 0 },
	   ".data" => { group => \@datagroup, size => 0 },
	   ".bss" => { group => \@bssgroup, size => 0 }
	   );

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

foreach $o (@objects) {
    print "visit $o->{name}, ";
    foreach $s (@{$o->{segs}}) {
	next unless $s;		# skip initial null
	# figure out which group this should be in
	my $group;

	print "\n  seg $s->{name}";
	if($s->{flags} !~ /P/) {
	    $group = \@bssgroup; # not present, must be BSS
	} elsif($s->{flags} =~ /W/) {
	    $group = \@datagroup; # writable, must be data
	} else {
	    $group = \@textgroup;
	}

	# see if already there
	my $g = $groups{$s->{name}};

	if($g) {
	    if($g->{group} ne $group) {
		die "Segment $o->{name}:$s->{name} inconsistent type";
	    }
	} else {
	    # make a new entry
	    $groups{$s->{name}} = $g = { group => $group, size => 0 };
	    push @$group, $s->{name};
	}
	$g->{size} += roundup($s->{size}, $wordalign);    
    }
}

# set the base of each segment in each group

$tbase = $textbase;
$tsize = 0;
print "text group\n";
foreach $s (@textgroup) {
    print "text $s: ";
    my $g = $groups{$s};
    $g->{base} = $tbase+$tsize;
    $g->{cbase} = $tbase+$tsize;	# running base when positioning segments below
    printf "%X (%X)\n", $g->{base}, $g->{size};
    $tsize += $g->{size};
}

$dbase = roundup($tbase+$tsize, $pagealign); # data is page aligned
$dsize = 0;

print "data group\n";
foreach $s (@datagroup) {
    print "data $s: ";
    my $g = $groups{$s};
    $g->{base} = $dbase+$dsize;
    $g->{cbase} = $dbase+$dsize;	# running base when positioning segments below
    printf "%X (%X)\n", $g->{base}, $g->{size};
    $dsize += $g->{size};
}

$bbase = roundup ($dbase+$dsize, $wordalign); # bss is word aligned
$bsize = 0;

print "bss group\n";
foreach $s (@bssgroup) {
    print "bss $s: ";
    my $g = $groups{$s};
    $g->{base} = $bbase+$bsize;
    $g->{cbase} = $bbase+$bsize;	# running base when positioning segments below
    printf "%X (%X)\n", $g->{base}, $g->{size};
    $bsize += $g->{size};
}

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

# now set the new base values for each segment in each module

foreach $o (@objects) {
    print "revisit $o->{name}, ";
    foreach $s (@{$o->{segs}}) {
	# figure out which group this should be in
	my $g = $groups{$s->{name}};

	$s->{oldbase} = $s->{base};
	$s->{base} = $g->{cbase};

	printf " %s:%s %X (%X)\n", $o->{name}, $s->{name}, $s->{base}, $s->{size};

	$g->{cbase} += roundup($s->{size}, $wordalign);
    }
}

# now find the commons
$cbase = roundup ($bbase+$bsize, $wordalign); # bss is word aligned
$csize = 0;

while (($n, $s) = each %sym) {
    next unless $s->{type} eq "U";

    my $v = $s->{value};

    if($v == 0) {
	print "Undefined $n\n";
    } else {
	$s->{type} = "D";
	$s->{value} = $cbase+$csize;
	# will have to note it's in .common in BSS
	$csize = roundup ($csize+$v, $wordalign); # bss is word aligned
	printf "Common $n size $v, location %X\n", $s->{value};
    }
}

# now create the output object

%out = (
    name => "a.out.lk",
    nsym => 0,
    nrel => 0,
    segs => [ undef ]
);

$segno = 0;

# text segments
foreach $s (@textgroup) {
    print "text $s: ";
    my $g = $groups{$s};

    $out{segnames}->{$s} = ++$segno;

    push @{$out{segs}}, 
	     {
		 name => $s,
		 segno => $segno,
		 base => $g->{base},
		 size => $g->{size},
		 flags => "RP",
	     };
    print "$segno $g->{base} $g->{size}\n";
}


# data segments
foreach $s (@datagroup) {
    print "data $s: ";
    my $g = $groups{$s};

    $out{segnames}->{$s} = ++$segno;

    push @{$out{segs}}, 
	     {
		 name => $s,
		 segno => $segno,
		 base => $g->{base},
		 size => $g->{size},
		 flags => "RWP",
	     };
    print "$segno $g->{base} $g->{size}\n";
}

# bss segments
foreach $s (@bssgroup) {
    print "bss $s: ";
    my $g = $groups{$s};

    $out{segnames}->{$s} = ++$segno;

    push @{$out{segs}},
	     {
		 name => $s,
		 segno => $segno,
		 base => $g->{base},
		 size => $g->{size},
		 flags => "RW",
	     };
    print "$segno $g->{base} $g->{size}\n";
}

# add last segment for common
if($csize) { 
    $out{segnames}->{".common"} = ++$segno;

    push @{$out{segs}},
	     {
		 name => ".common",
		 segno => $segno,
		 base => $cbase,
		 size => $csize,
		 flags => "RW",
	     };
    print ".common $segno $cbase $csize\n";
}
   
$out{nseg} = $segno;

writeobject($out{name}, \%out);
