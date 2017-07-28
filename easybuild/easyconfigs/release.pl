#!/usr/bin/env perl
use strict;
use warnings;
use File::Copy qw(copy);
use Data::Dumper;

#copy $old_file, $new_file;
my $sourcedir = "";

#print join("\n",glob("/data/umcg-mterpstra/apps//software/*/*/*/*.eb"))."\n";
my @ebs=glob("/data/umcg-mterpstra/apps//software/*/*/*/*.eb");
for my $eb (@ebs){
	chomp $eb;
	my $dname = `dirname $0`;
	#here : git/easybuild-easyconfigs/easybuild/easyconfigs
	chomp $dname;
	my $bname = `basename $eb`;
	chomp $bname;
	my $ebname = GetEbName($eb) or die "Could not detect easybuild file software name of $eb";
	#
	my $lcdir = $dname.'/'.lc(substr($ebname,0,1));
	#here git/easybuild-easyconfigs/easybuild/easyconfigs/a/
	chomp $lcdir;
        if( ! -e $lcdir){
                mkdir $lcdir;
        }
	#here git/easybuild-easyconfigs/easybuild/easyconfigs/a/aha
	my $sfnamedir = $lcdir.'/'.$ebname;
	if( ! -e $sfnamedir){
                mkdir $sfnamedir;
        }
	my $ebtarget = $sfnamedir.'/'.$bname;
	if( ! -e $ebtarget){
		copy ($eb, $ebtarget );
		warn "Copying '$eb' to '$ebtarget'";
		#
		my $sources = GetEbSource({'sourcedir'=>'/data/umcg-mterpstra/apps/sources/','eb'=>$ebtarget});
		AddEbChecksums({'sources' => $sources,'eb'=>$ebtarget});
		#die `cat $ebtarget`;

	}else{
		#warn "$ebtarget already present.".`diff $ebtarget $eb`;
	}
}


#sub basename {
#	my $p = shift @_;
#	$p =~ s/[^\/]{1,}$//g;
#	return $p;
#}

sub GetEbName {
	my $eb = shift(@_);
	my $ebname;
	open(my $ebh, '<', $eb) or die "Cannot open for read: $eb";
	while(<$ebh>){
		return $1 if(m/^name\s*=\s*['"]+(.*)['"]+/ ); 
	} 
	#return $ebname;
	die "Cannot find easybuild software name ";
}

sub GetEbVersion {
	my $eb = shift(@_);
	my $ebname;
	open(my $ebh, '<', $eb) or die "Cannot open for read: $eb";
	while(<$ebh>){
		return $1 if(m/^version\s*=\s*['"]+(.*)['"]+/ );
	}
	#return $ebname;
        die "Cannot find easybuild software version ";

}
sub GetEbVersionSuffix {
        my $eb = shift(@_);
        open(my $ebh, '<', $eb) or die "Cannot open for read: $eb";
        while(<$ebh>){
                return $1 if(m/^versionsuffix\s*=\s*['"]+(.*)['"]+/ );
        }
	#return $ebname;
        die "Cannot find easybuild software versionsuffix ";

}

sub GetEbSource {
	my $self = shift @_;
	#get /data/umcg-mterpstra/apps/sources/a/aha/0.4.9.tar.gz
	my $sourcedir = $self -> {'sourcedir'};
	my $eb = $self -> {'eb'};
	my $sfname = GetEbName($eb);
	open(my $ebh, '<', $eb) or die "Cannot open for read: $eb";
	my $sources;
        while(<$ebh>){
		if(m/^sources\s*=\s*\[(.*)\]/){
			my $sourcestring=$1;
			#strip parentesis;
			$sourcestring =~ s/^\s*\((.*)\)/$1/g;
			
			while($sourcestring =~ m/(\%\s\([^\)]*,[^)]*\))/){
				my $replace = $1;
				my $repNew = $replace;
				$repNew =~ s/,/#/g;
				substr($sourcestring,index($sourcestring,$replace),length($replace),$repNew);				
			}
			warn ' sourcestring='.$sourcestring;
			@{$sources} = split(',',$sourcestring);
			warn Dumper($sources)." ";
			$sources=CleanWhitespace($sources);
			$sources=SourcesExpander({'sources' => $sources, 'eb' => $eb});
		}
        }
	warn Dumper( $sources)." ";
	my $sourcefiles;
	for my $sourcefile (@{$sources}){
		if( -e $sourcedir.'/'.lc(substr($sfname,0,1)).'/'.$sfname.'/'. $sourcefile){
			push(@{$sourcefiles},$sourcedir.'/'.lc(substr($sfname,0,1)).'/'.$sfname.'/'.$sourcefile);
		}else{
			die "cannot find '$sourcedir/".lc(substr($sfname,0,1))."/$sfname/'$sourcefile'";
		}
	}
	#die Dumper($sourcefiles)." ";
	return $sourcefiles;
}

sub CleanWhitespace {
	my $arr=shift @_;
	my $arrNew;
	for my $val (@{$arr}){
		$val =~ s/^\s*|\s*$//g;
		push(@{$arrNew},$val);
	}
	return $arrNew;
}
#sub SetEbChecksum {
#	my $self = shift @_;
#	my $eb = $self -> {'eb'};
#       	my $sources =$self -> {'sources'};
#
#	
#	
#}
sub SourcesExpander {
	my $self = shift @_;

	my $eb = $self -> {'eb'};
	my $sources =$self -> {'sources'};
	my $sourcesNew;
	my $name = GetEbName($eb);
        my $version = GetEbVersion($eb);
	my $namelower = lc($name);#<<not from easybuild file and assumes things...
	warn Dumper($sources)." ";
	for my $source (@{$sources}){
		if($source =~ s/^SOURCE_TAR_GZ$/$name-$version.tar.gz/){
		}elsif($source =~ s/^SOURCELOWER_TAR_GZ$/$name-$version.tar.gz/){
			$source = lc($source);
               	}elsif($source =~ s/^SOURCE_TAR_XZ$/$name-$version.tar.xz/){
                }elsif($source =~ s/^SOURCELOWER_TAR_XZ$/$name-$version.tar.xz/){
                        $source = lc($source);
                }elsif($source =~ s/^SOURCE_TAR_BZ$/$name-$version.tar.bz/){
                }elsif($source =~ s/^SOURCELOWER_TAR_BZ$/$name-$version.tar.bz/){
                        $source = lc($source);
                }elsif($source =~ s/^SOURCE_TAR_BZ2$/$name-$version.tar.bz2/){
                }elsif($source =~ s/^SOURCELOWER_TAR_BZ2$/$name-$version.tar.bz2/){
                        $source = lc($source);
                }elsif($source =~ m/\%s/){
			my ($string,$replacement) = split /\s+\%\s+/,$source;
			$replacement =~ s/\(|\)|\s*//g;
			for my $rep (split('#',$replacement)){
				if($rep eq 'version'){
					warn "replaced". substr($string,index($string,'%s'),2,$version).$string ;
				}elsif($rep eq 'name'){
					warn "replaced". substr($string,index($string,'%s'),2,$name).$string ;
				}elsif($rep eq 'namelower'){
                                        warn "replaced". substr($string,index($string,'%s'),2,$namelower).$string ;
                                }else{
					die substr($string,index($string,'%s'),2,$rep).$string;
				}
				
			}
			$source=$string;
		}
		if($source =~ s/\%\(name\)s/$name/g){
			#warn 
		}
		if($source =~ m/(\%\(namelower\)s)/){
                        substr($source,index($source,$1),length($1),lc($name));
                }
		if($source =~ s/\%\(version\)s/$version/g){
		}
		if($source =~ m/\%\(versionsuffix\)s/){
			my $versuffix = GetEbVersionSuffix($eb);
			$source =~ s/\%\(versionsuffix\)s/$versuffix/g;
		}
		#remove trailing quotations
		$source =~  s/^\"|^\'|\'$|\"$//g;
		push(@{$sourcesNew},$source);
		
	}
	warn Dumper($sourcesNew)." " ;
	return $sourcesNew;
}
sub AddEbChecksums {
	my $self = shift @_;
	my $eb = $self -> {'eb'};
	my $sources =$self -> {'sources'};

	my $chksums = GetChecksumSources($sources);
	
	open(my $ebh, '<', $eb) or die "Cannot open for read: $eb";
        chomp(my @eblines = <$ebh>);
	close $ebh;
	
	for my $ebline (@eblines){
		return 1 if($ebline =~ m/^checksums\s*=\s/);
	}
	
	open(my $ebha, '>>', $eb) or die "Cannot open for read: $eb";
	print {$ebha} "\nchecksums = ['".join("','",@{$chksums})."']"; 
	return 1;
	#while(<$ebha>){
        #        return $1 if(m/^version\s*=\s*['"]+(.*)['"]+/ );
        #}

}

sub GetChecksumSources {
	my $sources = shift @_;
	my $checksums;
	for my $source (@{$sources}){
		my $cmd ="md5sum $source | cut -d' ' -f1 ";
		my $chksum = `$cmd`;
		chomp($chksum);
		push(@{$checksums},$chksum);
	}
	
	return $checksums;
}
