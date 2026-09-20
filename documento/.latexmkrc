# Auxiliares em build/; o PDF é copiado para a raiz no fim.
use File::Basename qw(fileparse);
use File::Spec;

$out_dir = 'build';
$aux_dir = 'build';
$pdf_mode = 1;

add_cus_dep( 'acn', 'acr', 0, 'makeglossaries' );
add_cus_dep( 'glo', 'gls', 0, 'makeglossaries' );
$clean_ext .= " acr acn alg glo gls glg ist glsdefs";

# \printglossary / \printacronyms fazem \input{jobname.gls/.acr}.
# Com -outdir, esses ficheiros ficam em build/; o TEXINPUTS aponta para lá
# em vez de os copiar para a raiz.
ensure_path('TEXINPUTS', 'build');

# TeX Live's fat biber (PAR) calls lipo with flag-first syntax.
# On recent macOS that fails, so peel the native slice once.
if ($^O eq 'darwin') {
  my $src  = '/Library/TeX/texbin/biber';
  my $thin = '/tmp/biber-arm64-tl';
  if (-x $src && !-x $thin) {
    system('/usr/bin/lipo', $src, '-thin', 'arm64', '-output', $thin);
    chmod 0755, $thin if -f $thin;
  }
  $biber = "\"$thin\" %O %S" if -x $thin;
}

sub makeglossaries {
     my ($base_name, $path) = fileparse( $_[0] );
     $path = $out_dir unless defined $path && $path ne '';
     my @args = ( "-d", $path, $base_name );
     if ($silent) { unshift @args, "-q"; }
     return system "makeglossaries", @args;
}

$success_cmd = 'cp -f %D main.pdf';
