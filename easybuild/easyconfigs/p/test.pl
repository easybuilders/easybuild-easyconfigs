use strict;
 use Test::More;
use Config;
    my $tainted_path = substr($^X,0,0) . "/no/such/file";
    my $err;
    # $! is used in a tainted expression, so gets tainted
    open my $fh, $tainted_path or $err= "$!";
    unlike($err, qr/^\d+$/, 'tainted $!');
