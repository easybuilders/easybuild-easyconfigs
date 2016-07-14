wget https://github.com/molgenis/ngs-utils/releases/download/15.11.1/PPVforNIPT_0.1.tar.gz
mv PPVforNIPT_0.1.tar.gz /apps/data/NIPT/
module load R
R CMD INSTALL /apps/data/NIPT/PPVforNIPT_0.1.tar.gz
