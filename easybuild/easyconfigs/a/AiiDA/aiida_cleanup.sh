#!/usr/bin/env bash

module load RabbitMQ
module load PostgreSQL
module load aiida-core

echo "WARNING: this script will completely remove all data from the AiiDA database, repository and configuration."
read -p "Are you sure you want to continue? [y/N] " -n 1 -r REPLY

if [[ ! "$REPLY" == "y" ]]; then
    echo "Aborting."
    exit 1
fi

LOGHEADER="== "

AIIDA_LOGHEADER="${LOGHEADER}AiiDA:"
RMQ_LOGHEADER="${LOGHEADER}RabbitMQ:"
PG_LOGHEADER="${LOGHEADER}PostgreSQL:"

PGDATA="`cat $EB_CONFIG_DIR/psql_datadir`"
AIIDA_DIR="`cat ${EB_CONFIG_DIR}/aiida_dir`"

echo "${AIIDA_LOGHEADER} Stopping AiiDA daemon"
verdi daemon stop
echo "${RMQ_LOGHEADER} Stopping RabbitMQ"
rabbitmqctl stop 2> /dev/null
echo "${PG_LOGHEADER} Stopping PostgreSQL"
pg_ctl stop -D $PGDATA 2> /dev/null

echo "${AIIDA_LOGHEADER} Removing AiiDA database"
rm -rf $PGDATA
echo "${AIIDA_LOGHEADER} Removing AiiDA repository"
rm -rf $AIIDA_DIR
echo "${AIIDA_LOGHEADER} Removing the AiiDA configuration file"
rm -rf $HOME/.aiida
echo "${LOGHEADER} Removing the configuration folder"
rm -rf $EB_CONFIG_DIR
