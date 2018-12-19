module purge
module load EasyBuild
module list

wk_dir=/groups/umcg-gcc/tmp04/CADD
ec_path=${wk_dir}/easyconfigs
cadd_v1_4_path=${ec_path}/easybuild/easyconfigs/c/CADD/
pp_path=${ec_path}/easybuild/easyconfigs/p/PythonPlus/

global_ec_path=/apps/source/EasyBuild

#
# if you deploy CADD v1.4 globaly, please skip it by commenting it
#
source ${wk_dir}/modules/modules.bashrc


#
# deploying PythonPlus, including dependencies for CADD v1.4
#
eb ${pp_path}/PythonPlus-2.7.12-foss-2015b-v18.11.1.eb \
    --robot \
    --robot-path ${global_ec_path}

#
# deploying CADD v1.4, including scripts and databases
#
eb ${cadd_v1_4_path}/CADD-v1.4.eb \
    --robot \
    --robot-path ${global_ec_path}

#
# test whether the CADD/v1.4 is loadable
#
module load CADD/v1.4
CADD.sh -h

#
# test whether the CADD/v1.4 is executable
#
CADD.sh -a \
    -g GRCh37 \
    -o ${EBROOTCADD}/CADD_v1.4_test_output.tsv.gz \
    ${EBROOTCADD}/test/input.vcf

if [[ $? -eq 0 ]]; then
    echo "Please check ${EBROOTCADD}/CADD_v1.4_test_output.tsv.gz"
else
    echo "There's issue when doing test"
fi
